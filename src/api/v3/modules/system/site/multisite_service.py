"""多站点：域名解析 + 用户归属（v3 真实实现）

替代 v2 的 ``shared/services/system/multisite_service.py``（423 行）里 CRUD 之外的能力。
v3 的 ``system/site`` 已覆盖站点 CRUD（slug 锁定、domain 唯一、``is_default`` 全站唯一），
本模块补齐用户明确需要的两块：

  - **域名解析**：按 Host 定位站点 —— 主域名 ``sites.domain`` 与附加域名
    ``sites.additional_domains``（文本，逗号/分号/换行分隔）都参与匹配
  - **用户归属**：站点成员（``site_users``：role / is_active / joined_at）增删查，
    以及"某用户属于哪些站点"

**明确不做的部分**：跨站内容复制（``content_mappings``）需要按内容类型逐个设计
（文章/页面/分类的外键与 SEO 关系），本批不实现 —— 宁可不做，也不留"只记录不同步"的假能力。
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.multisite.site import Site
from shared.models.multisite.site_user import SiteUser
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("system.multisite")

#: 附加域名分隔符（兼容逗号 / 分号 / 空白）
_DOMAIN_SPLIT = re.compile(r"[\s,;]+")


def split_domains(raw: Optional[str]) -> List[str]:
    """解析 ``additional_domains`` 为规范化域名列表

    存储格式与 v3 既有约定一致（**JSON 数组**，见 ``SiteOut`` 的 JSON 解析器），
    同时兼容历史/手填的逗号分隔文本。
    """
    if not raw:
        return []
    text = raw.strip()
    items: List[str] = []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                items = [str(item) for item in parsed]
        except (ValueError, TypeError):
            items = []
    if not items:
        items = _DOMAIN_SPLIT.split(text)

    result: List[str] = []
    for item in items:
        domain = normalize_domain(item)
        if domain and domain not in result:
            result.append(domain)
    return result


def normalize_domain(value: Optional[str]) -> str:
    """规范化域名：去协议/路径/端口/首尾通配，统一小写"""
    text = (value or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"^https?://", "", text)
    text = text.split("/", 1)[0]
    text = text.split(":", 1)[0]
    # 去掉通配符与误入的 JSON/列表符号（域名本身不含方括号）
    return text.strip("*. []")


def join_domains(domains: List[str]) -> str:
    """序列化为 JSON 数组（与 v3 既有 ``additional_domains`` 约定一致）"""
    return json.dumps(domains, ensure_ascii=False)


class MultiSiteService:
    """域名解析与站点成员管理"""

    # ------------------------------------------------------------------ 域名
    async def resolve_by_domain(self, db: AsyncSession, domain: str) -> Dict[str, Any]:
        """按域名找站点：主域名精确优先，其次附加域名包含

        找不到时回退到默认站点（``is_default``）—— 前台首次部署/本地调试常见
        "域名还没配"的情况，回退默认站比直接 404 更好用；但仍会返回 ``matched=False``
        让调用方知道这是回退结果。
        """
        target = normalize_domain(domain)
        if not target:
            raise BadRequestError("domain 不能为空")

        rows = (
            await db.execute(select(Site).where(Site.is_active.is_(True)))
        ).scalars().all()

        for site in rows:
            if normalize_domain(site.domain) == target:
                return {"matched": True, "match": "primary", **self._site_out(site)}
        for site in rows:
            if target in split_domains(site.additional_domains):
                return {"matched": True, "match": "additional", **self._site_out(site)}

        default_site = next((site for site in rows if site.is_default), None)
        if default_site is None:
            raise NotFoundError(f"域名 {target} 未绑定任何站点")
        return {"matched": False, "match": "default", **self._site_out(default_site)}

    async def set_domains(
        self,
        db: AsyncSession,
        site_id: int,
        *,
        domain: Optional[str] = None,
        additional_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """设置主域名与附加域名（域名全局唯一，冲突直接拒绝）"""
        site = await db.get(Site, site_id)
        if site is None:
            raise NotFoundError("站点不存在")

        if domain is not None:
            normalized = normalize_domain(domain)
            if not normalized:
                raise BadRequestError("主域名不能为空")
            existing = (
                await db.execute(
                    select(Site).where(
                        func.lower(Site.domain) == normalized, Site.id != site_id
                    )
                )
            ).scalars().first()
            if existing is not None:
                raise ConflictError(f"域名 {normalized} 已被站点「{existing.name}」占用")
            site.domain = normalized

        if additional_domains is not None:
            cleaned = [normalize_domain(item) for item in additional_domains]
            cleaned = [item for item in cleaned if item]
            primary = normalize_domain(site.domain)
            duplicates = [item for item in cleaned if item == primary]
            if duplicates:
                raise BadRequestError("附加域名不能与主域名相同")
            site.additional_domains = join_domains(cleaned) if cleaned else None

        site.updated_at = datetime.now()
        await db.commit()
        await db.refresh(site)
        logger.info("站点 %s 域名更新：primary=%s additional=%s", site_id, site.domain, site.additional_domains)
        return self._site_out(site, with_domains=True)

    async def set_default(self, db: AsyncSession, site_id: int) -> Dict[str, Any]:
        """设为默认站点（``is_default`` 全站唯一）"""
        site = await db.get(Site, site_id)
        if site is None:
            raise NotFoundError("站点不存在")
        await db.execute(
            Site.__table__.update().where(Site.is_default.is_(True)).values(is_default=False)
        )
        site.is_default = True
        site.updated_at = datetime.now()
        await db.commit()
        await db.refresh(site)
        return self._site_out(site)

    # ------------------------------------------------------------------ 成员
    async def list_members(
        self,
        db: AsyncSession,
        site_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        site = await db.get(Site, site_id)
        if site is None:
            raise NotFoundError("站点不存在")

        condition = [SiteUser.site_id == site_id]
        total = int(
            (await db.execute(select(func.count()).select_from(SiteUser).where(*condition))).scalar()
            or 0
        )
        rows = (
            await db.execute(
                select(SiteUser)
                .where(*condition)
                .order_by(SiteUser.id.asc())
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return [self._member_out(row) for row in rows], total

    async def add_member(
        self,
        db: AsyncSession,
        site_id: int,
        *,
        user_id: int,
        role: str = "member",
        is_active: bool = True,
    ) -> Dict[str, Any]:
        """把用户加入站点（重复加入直接拒绝，避免脏数据）"""
        site = await db.get(Site, site_id)
        if site is None:
            raise NotFoundError("站点不存在")

        existing = (
            await db.execute(
                select(SiteUser).where(SiteUser.site_id == site_id, SiteUser.user_id == user_id)
            )
        ).scalars().first()
        if existing is not None:
            # 已存在：更新角色/启用状态（比报错更好用），并标记为"更新"
            existing.role = role
            existing.is_active = is_active
            await db.commit()
            await db.refresh(existing)
            logger.info("站点成员已更新 site=%s user=%s role=%s", site_id, user_id, role)
            return {"created": False, **self._member_out(existing)}

        now = datetime.now()
        row = SiteUser(
            site_id=site_id,
            user_id=user_id,
            role=role,
            is_active=is_active,
            joined_at=now,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info("站点成员已加入 site=%s user=%s role=%s", site_id, user_id, role)
        return {"created": True, **self._member_out(row)}

    async def remove_member(self, db: AsyncSession, site_id: int, user_id: int) -> None:
        row = (
            await db.execute(
                select(SiteUser).where(SiteUser.site_id == site_id, SiteUser.user_id == user_id)
            )
        ).scalars().first()
        if row is None:
            raise NotFoundError("该用户不在此站点中")
        await db.delete(row)
        await db.commit()

    async def user_sites(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """某用户所属的站点（含角色与启用状态）"""
        rows = (
            await db.execute(
                select(SiteUser, Site)
                .join(Site, Site.id == SiteUser.site_id)
                .where(SiteUser.user_id == user_id, SiteUser.is_active.is_(True))
                .order_by(SiteUser.id.asc())
            )
        ).all()
        return {
            "user_id": user_id,
            "items": [
                {
                    **self._site_out(site),
                    "role": member.role,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                }
                for member, site in rows
            ],
        }

    # ------------------------------------------------------------------ 输出
    @staticmethod
    def _member_out(row: SiteUser) -> Dict[str, Any]:
        return {
            "id": row.id,
            "site_id": row.site_id,
            "user_id": row.user_id,
            "role": row.role,
            "is_active": bool(row.is_active),
            "joined_at": row.joined_at.isoformat() if row.joined_at else None,
        }

    @staticmethod
    def _site_out(site: Site, *, with_domains: bool = False) -> Dict[str, Any]:
        data = {
            "id": site.id,
            "name": site.name,
            "slug": site.slug,
            "domain": site.domain,
            "theme": site.theme,
            "language": site.language,
            "timezone": site.timezone,
            "logo_url": site.logo_url,
            "favicon_url": site.favicon_url,
            "is_active": bool(site.is_active),
            "is_default": bool(site.is_default),
        }
        if with_domains:
            data["additional_domains"] = split_domains(site.additional_domains)
        return data


multisite_service = MultiSiteService()
