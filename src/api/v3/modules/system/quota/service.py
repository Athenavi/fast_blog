"""站点配额（site quota）：配额持久化 + 真实用量统计 + 配额校验

源能力来自 v2 的 ``shared/services/system/site_quota_service.py``。v2 版本有两处**实际失效**：

1. **用量统计恒为 0**。v2 的 ``_calculate_usage`` 用 ``Article.site_id`` /
   ``User.site_id`` / ``Media.site_id`` / ``Category.site_id``，但本项目的 schema 里
   ``articles`` / ``media`` / ``users`` / ``categories`` **都没有 site_id 列**
   （见初始迁移 ``alembic_migrations`` 与 ``shared/models/**``）——这些属性访问会抛
   ``AttributeError``，被方法里的 ``try/except`` 吞掉，于是用量恒为 0，配额校验等于没做。

2. **settings 被当 dict 用**。v2 直接 ``site.settings.get('quotas')`` /
   ``site.settings['quotas'] = ...``，但 ``sites.settings`` 列是 **Text**（内容为 JSON 字符串），
   ORM 返回 ``str``，``.get`` / 下标赋值都会失败。

v3 重写要点：

- 配额存 ``sites.settings``（Text 列，里面是 JSON 对象）的 ``quota`` 键，读写都走
  ``json.dumps`` / ``json.loads``（绝不做字符串拼接）。
- 用量**真实统计**（真表 ``count`` / ``sum``）：

  * ``users`` = ``site_users`` 中该站点的成员数（该表有 ``site_id`` 列，精确）；
  * ``articles`` / ``media`` / ``storage_mb`` 因 ``articles`` / ``media`` 表**没有** ``site_id``，
    改用「站点成员（``site_users``）创建的文章 / 上传的媒体」这一可解释口径统计——
    数字来自真实表，无任何 mock / 硬编码；口径与局限在 ``USAGE_SCOPE`` 里如实标注。

- 纯函数（``is_unlimited`` / ``quota_percent`` / ``quota_remaining`` / ``summarize`` /
  ``parse_settings`` / ``resolve_quota`` / ``ensure_resource_type`` /
  ``validate_quota_update`` / ``check_resource``）与 DB 读写彻底分离，便于无库测试。
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.media.media import Media
from shared.models.multisite.site import Site
from shared.models.multisite.site_user import SiteUser
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("system.quota")

#: 配额在 ``sites.settings``（Text，存 JSON 对象）里占用的键
QUOTA_SETTINGS_KEY = "quota"

#: 默认配额上限；``0`` 或 ``null`` 表示**不限**
DEFAULT_QUOTA: Dict[str, Any] = {
    "articles": 10000,
    "media": 5000,
    "users": 1000,
    "storage_mb": 5120,
}

#: 受支持的资源类型（= 配额键，顺序与 ``DEFAULT_QUOTA`` 一致）
RESOURCE_TYPES = tuple(DEFAULT_QUOTA)

#: 各资源用量的统计口径（如实说明关联到什么程度）
USAGE_SCOPE: Dict[str, str] = {
    "users": "site_users 精确计数（该表有 site_id 列）",
    "articles": "站点成员（site_users）创建的文章数；articles 表无 site_id 列，按成员归属",
    "media": "站点成员上传的媒体数；media 表无 site_id 列，按成员归属",
    "storage_mb": "站点成员上传媒体的字节合计换算为 MB；media 表无 site_id 列，按成员归属",
}


# ------------------------------------------------------------------ 纯函数：配额语义
def is_unlimited(limit: Any) -> bool:
    """``None`` 或 ``0`` 表示不限配额"""
    return limit is None or limit == 0


def quota_percent(usage: Optional[int], limit: Any) -> Optional[float]:
    """用量占上限的百分比（四舍五入两位）；用量未知或不限配额时返回 ``None``"""
    if usage is None or is_unlimited(limit):
        return None
    return round(usage / limit * 100, 2)


def quota_remaining(usage: Optional[int], limit: Any) -> Optional[int]:
    """剩余可用量（不为负）；用量未知或不限配额时返回 ``None``"""
    if usage is None or is_unlimited(limit):
        return None
    return max(limit - usage, 0)


def summarize(quota: Dict[str, Any], usage: Dict[str, Any]) -> Dict[str, Any]:
    """汇总出 ``remaining`` / ``usage_percent`` / ``exceeded``

    - ``exceeded``：用量**已达或超过**上限（``>= limit``）的资源，意味着无法再增；
    - 用量为 ``None``（该资源无法统计）不计入 ``exceeded``，对应项也返回 ``None``。
    """
    remaining: Dict[str, Optional[int]] = {}
    usage_percent: Dict[str, Optional[float]] = {}
    exceeded: list[str] = []
    for resource in RESOURCE_TYPES:
        limit = quota.get(resource)
        current = usage.get(resource)
        remaining[resource] = quota_remaining(current, limit)
        usage_percent[resource] = quota_percent(current, limit)
        if current is not None and not is_unlimited(limit) and current >= limit:
            exceeded.append(resource)
    return {
        "remaining": remaining,
        "usage_percent": usage_percent,
        "exceeded": exceeded,
    }


def parse_settings(raw: Any) -> Dict[str, Any]:
    """把 ``sites.settings`` 解析为 dict（兼容 dict / JSON 字符串 / 损坏值）

    非对象、空串或解析失败一律返回空 dict——一个坏配置不应该让整站读不到用量。
    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = bytes(raw).decode("utf-8")
        except UnicodeDecodeError:
            return {}
    if not isinstance(raw, str):
        return {}
    text = raw.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def resolve_quota(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """由 ``site.settings`` 解析出的 dict 得到完整配额

    已知键以存量值为准（``null`` 表示不限），未知键忽略，非法值（负数 / 非整数 / 布尔）
    回退到 ``DEFAULT_QUOTA``。
    """
    quota = dict(DEFAULT_QUOTA)
    stored = (settings or {}).get(QUOTA_SETTINGS_KEY)
    if isinstance(stored, dict):
        for key, value in stored.items():
            if key not in RESOURCE_TYPES:
                continue
            if value is None or (
                isinstance(value, int) and not isinstance(value, bool) and value >= 0
            ):
                quota[key] = value
    return quota


def ensure_resource_type(resource_type: Any) -> str:
    """校验资源类型，非法时抛 ``BadRequestError``"""
    if resource_type not in RESOURCE_TYPES:
        raise BadRequestError(
            f"未知的资源类型「{resource_type}」（可选：{list(RESOURCE_TYPES)}）"
        )
    return str(resource_type)


def validate_quota_update(quotas: Any) -> Dict[str, Optional[int]]:
    """校验并归一化一份配额更新（未知键 / 负值 / 非整数一律 ``BadRequestError``）

    合法值为**非负整数**（``0`` 表示不限）或 ``null``（不限）。布尔值被明确拒绝
    （Python 里 ``True`` 也是 ``int``，不拦会悄悄变成 1）。
    """
    if not isinstance(quotas, dict):
        raise BadRequestError("quotas 必须是 JSON 对象（dict）")

    unknown = [key for key in quotas if key not in RESOURCE_TYPES]
    if unknown:
        raise BadRequestError(
            f"未知的配额项：{unknown}（可选：{list(RESOURCE_TYPES)}）"
        )

    clean: Dict[str, Optional[int]] = {}
    for key, value in quotas.items():
        if value is None:
            clean[key] = None
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            raise BadRequestError(
                f"配额「{key}」必须是非负整数或 null（表示不限），收到 {value!r}"
            )
        if value < 0:
            raise BadRequestError(f"配额「{key}」不能为负数，收到 {value}")
        clean[key] = value
    return clean


def check_resource(
    resource_type: str,
    requested_amount: int,
    quota: Dict[str, Any],
    usage: Dict[str, Any],
) -> Dict[str, Any]:
    """纯配额校验：追加 ``requested_amount`` 后是否仍在配额内

    返回 ``{allowed, resource_type, reason, current, limit, remaining}``。非法资源类型 /
    非法数量抛 ``BadRequestError``。用量未知的资源不拦（``allowed=True`` 且 ``reason`` 说明）。
    """
    ensure_resource_type(resource_type)
    if isinstance(requested_amount, bool) or not isinstance(requested_amount, int):
        raise BadRequestError(f"requested_amount 必须是整数，收到 {requested_amount!r}")
    if requested_amount < 0:
        raise BadRequestError(f"requested_amount 不能为负数，收到 {requested_amount}")

    limit = quota.get(resource_type)
    current = usage.get(resource_type)

    if is_unlimited(limit):
        return {
            "allowed": True,
            "resource_type": resource_type,
            "reason": "该资源不限配额",
            "current": current,
            "limit": None,
            "remaining": None,
        }
    if current is None:
        return {
            "allowed": True,
            "resource_type": resource_type,
            "reason": "该资源用量无法统计，未做配额校验（见 usage_scope）",
            "current": None,
            "limit": limit,
            "remaining": None,
        }

    remaining = quota_remaining(current, limit)
    allowed = current + requested_amount <= limit
    reason = (
        "配额充足"
        if allowed
        else f"配额不足：剩余 {remaining}，请求 {requested_amount}"
    )
    return {
        "allowed": allowed,
        "resource_type": resource_type,
        "reason": reason,
        "current": current,
        "limit": limit,
        "remaining": remaining,
    }


# ------------------------------------------------------------------ 服务（DB 读写）
class SiteQuotaService:
    """站点配额读写：配额存 ``sites.settings``，用量按真表统计"""

    # ------------------------------------------------------------------ 读
    @staticmethod
    def _load_quota(site: Site) -> Dict[str, Any]:
        """从站点行读出完整配额（缺失 / 损坏时回退默认）"""
        return resolve_quota(parse_settings(site.settings))

    async def _usage(self, db: AsyncSession, site_id: int) -> Dict[str, Any]:
        """真实统计该站点的资源用量

        - ``users``：``site_users`` 精确计数；
        - ``articles`` / ``media`` / ``storage_mb``：按站点成员口径（见 ``USAGE_SCOPE``），
          数字来自 ``articles`` 的 ``count`` 与 ``media`` 的 ``count`` / ``sum(file_size)``。
        """
        member_ids = list(
            (
                await db.execute(
                    select(SiteUser.user_id).where(SiteUser.site_id == site_id)
                )
            ).scalars().all()
        )
        users = len(member_ids)

        articles = 0
        media_count = 0
        media_bytes = 0
        if member_ids:
            articles = int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(Article)
                        .where(Article.user.in_(member_ids))
                    )
                ).scalar()
                or 0
            )
            media_count, media_bytes = (
                await db.execute(
                    select(
                        func.count(Media.id),
                        func.coalesce(func.sum(Media.file_size), 0),
                    ).where(Media.user.in_(member_ids))
                )
            ).one()

        return {
            "articles": articles,
            "media": int(media_count or 0),
            "users": users,
            "storage_mb": round(int(media_bytes or 0) / (1024 * 1024), 2),
        }

    async def get(self, db: AsyncSession, site_id: int) -> Dict[str, Any]:
        """配额 + 用量 + 剩余 / 占比 / 超限项"""
        site = await db.get(Site, site_id)
        if site is None:
            raise NotFoundError("站点不存在")

        quota = self._load_quota(site)
        usage = await self._usage(db, site_id)
        summary = summarize(quota, usage)
        return {
            "site_id": site_id,
            "site_name": site.name,
            "quota": quota,
            "usage": usage,
            "remaining": summary["remaining"],
            "usage_percent": summary["usage_percent"],
            "exceeded": summary["exceeded"],
            "usage_scope": dict(USAGE_SCOPE),
        }

    async def check(
        self,
        db: AsyncSession,
        site_id: int,
        resource_type: str,
        requested_amount: int = 1,
    ) -> Dict[str, Any]:
        """检查追加 ``requested_amount`` 后是否仍在配额内（资源类型非法 → 400）"""
        site = await db.get(Site, site_id)
        if site is None:
            raise NotFoundError("站点不存在")

        quota = self._load_quota(site)
        usage = await self._usage(db, site_id)
        return check_resource(resource_type, requested_amount, quota, usage)

    # ------------------------------------------------------------------ 写
    async def update(
        self, db: AsyncSession, site_id: int, quotas: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新站点配额并写回 ``sites.settings``（未知键 / 负值 / 非整数 → 400）"""
        site = await db.get(Site, site_id)
        if site is None:
            raise NotFoundError("站点不存在")

        clean = validate_quota_update(quotas)
        settings = parse_settings(site.settings)
        merged = {**resolve_quota(settings), **clean}

        settings[QUOTA_SETTINGS_KEY] = merged
        site.settings = json.dumps(settings, ensure_ascii=False)
        site.updated_at = datetime.now()
        await db.commit()
        logger.info("站点 %s 配额已更新：%s", site_id, sorted(clean) or "无")
        return {
            "site_id": site_id,
            "quota": merged,
            "updated": sorted(clean),
        }


#: 单例实例
site_quota_service = SiteQuotaService()
