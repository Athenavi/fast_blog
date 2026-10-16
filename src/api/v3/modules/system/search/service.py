"""search 模块业务逻辑：Meilisearch 连接配置（后台可改）+ 真实连通性 / 索引操作

## 配置存哪、为什么不需要迁移

与 `system/oauth` 的 `oauth.providers` 同一约定：配置存 ``system_settings`` 的 JSON 键
``search.meilisearch``，是**运行期按需写入**的配置项，不进任何 alembic 迁移。

## 配置改了怎么立即生效

``meilisearch_service`` 是**模块级单例**，而配置在**数据库**里。所以保存配置后必须
立刻把新值推给单例（``configure()`` 会重建客户端并清掉"不可用"标记）——
否则管理员改完 host 要重启服务才生效，那就是"配了没用"。

## 不伪造成功

本模块的连通性测试与索引操作**全部真做**：

  - ``test_connection`` 真的打一次 ``/health`` 与 ``/version``，连不上就 ``ok=False``
    并带上真实原因（超时 / 401 / DNS），**不返回好看的"测试通过"**；
  - ``stats`` 引擎不可用时 ``available=False``，**不报 0 冒充"空索引"**；
  - ``reindex`` 真查库、真写索引，返回真实计数。

这与 ``system/oauth`` 模块文档里那句"配置缺失即如实报'未配置'，不伪造成功"是同一条原则。
"""

import json
import os
import time
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.services.integrations.meilisearch_service import meilisearch_service
from src.api.v3.core.logger import get_logger
from src.api.v3.core.tenancy import apply_site_scope
from src.api.v3.modules.system.search.schema import SearchConfigUpdate
from src.api.v3.modules.system.setting.service import setting_service

logger = get_logger("system.search")

#: ``system_settings`` 中承载 Meilisearch 连接配置的 JSON 键
MEILISEARCH_SETTING_KEY = "search.meilisearch"
#: 索引名默认值（与 `meilisearch_service.DEFAULT_INDEX_NAME` 保持一致）
DEFAULT_INDEX_NAME = "articles"
#: 与 `article/service.py::_published_stmt` 一致：1 = 已发布
STATUS_PUBLISHED = 1


def parse_meili_config(setting_value: Optional[str]) -> dict:
    """把 ``system_settings`` 里的字符串值解析成配置字典（纯函数；损坏即回退空字典）

    与 ``oauth.parse_providers_config`` 同一写法：解析失败不当异常抛，
    因为"配置写坏了"不该让整个搜索设置页打不开 —— 应当显示为"未配置"。
    """
    if not setting_value:
        return {}
    try:
        parsed = json.loads(setting_value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def env_config() -> dict:
    """环境变量侧配置（**兜底**，不覆盖数据库配置）

    数据库里配了就用数据库的；没配才回落到环境变量 —— 这样已有部署（用 `.env` 配的）
    不会因为升级而突然失效，而管理员又能通过后台覆盖它。
    """
    return {
        "host": (os.getenv("MEILISEARCH_HOST") or "").strip(),
        "api_key": (os.getenv("MEILISEARCH_API_KEY") or "").strip(),
        "index_name": (os.getenv("MEILISEARCH_INDEX_NAME") or "").strip(),
    }


def _normalize(raw: dict, *, fallback: dict) -> dict:
    """把配置字典规范化（纯函数）

    ``host`` 为空即视为**未配置**：只有 host 才有"该不该启用"的判断意义 ——
    没有地址就没有可连的东西。
    """
    host = str(raw.get("host") or fallback.get("host") or "").strip()
    api_key = raw.get("api_key")
    if api_key is None:
        api_key = fallback.get("api_key") or ""
    index_name = str(raw.get("index_name") or fallback.get("index_name") or DEFAULT_INDEX_NAME).strip()
    return {
        "enabled": bool(raw.get("enabled", bool(host))),
        "host": host,
        "api_key": str(api_key or ""),
        "index_name": index_name or DEFAULT_INDEX_NAME,
    }


class SearchSettingsService:
    """Meilisearch 连接配置与索引操作"""

    async def _read_raw(self, db: AsyncSession) -> dict:
        """读原始配置（键不存在时返回空字典，**不抛异常** —— 未配置是正常状态）"""
        try:
            setting = await setting_service.get_setting(db, MEILISEARCH_SETTING_KEY)
        except Exception:
            # `get_setting` 在键不存在时抛 NotFoundError；未配置不是错误
            return {}
        return parse_meili_config(setting.get("setting_value"))

    async def get_config(self, db: AsyncSession) -> dict:
        """读连接配置（**脱敏**：只给 has_api_key，不回显密钥）"""
        raw = await self._read_raw(db)
        env = env_config()
        effective = _normalize(raw, fallback=env)
        return {
            "enabled": effective["enabled"],
            "host": effective["host"],
            "index_name": effective["index_name"],
            "has_api_key": bool(effective["api_key"]),
            "env_host": env["host"] or None,
            "env_has_api_key": bool(env["api_key"]),
        }

    async def update_config(self, db: AsyncSession, payload: SearchConfigUpdate) -> dict:
        """保存配置并**立即推给单例**（不重启即生效）"""
        raw = await self._read_raw(db)
        current_key = str(raw.get("api_key") or env_config()["api_key"] or "")

        if payload.clear_api_key:
            api_key = ""
        elif payload.api_key is None or not payload.api_key.strip():
            # 留空 = 保持原值（前端不必回填密钥，避免密钥来回传输）
            api_key = current_key
        else:
            api_key = payload.api_key.strip()

        stored = {
            "enabled": bool(payload.enabled),
            "host": payload.host.strip(),
            "api_key": api_key,
            "index_name": payload.index_name.strip() or DEFAULT_INDEX_NAME,
        }
        await setting_service.upsert(
            db,
            MEILISEARCH_SETTING_KEY,
            value=json.dumps(stored, ensure_ascii=False),
            setting_type="json",
            description="Meilisearch 连接配置（后台可改；api_key 不回显）",
            is_public=False,
        )
        # 立即生效：把新配置推给模块级单例（会重建客户端并清掉"不可用"标记）
        meilisearch_service.configure(
            host=stored["host"],
            api_key=stored["api_key"],
            index_name=stored["index_name"],
            enabled=stored["enabled"],
        )
        logger.info("Meilisearch 配置已更新并生效（host=%s, enabled=%s）", stored["host"], stored["enabled"])
        return await self.get_config(db)

    async def test_connection(self, db: AsyncSession) -> dict:
        """真实连通性测试（**不伪造成功**）"""
        config = await self.get_config(db)
        if not config["host"]:
            return {"ok": False, "message": "尚未配置 Meilisearch 地址"}

        started = time.monotonic()
        try:
            version = await meilisearch_service.probe()
        except Exception as exc:  # noqa: BLE001 - 真实原因要原样告诉管理员
            return {
                "ok": False,
                "message": f"连接失败：{type(exc).__name__}: {exc}",
                "latency_ms": int((time.monotonic() - started) * 1000),
            }
        return {
            "ok": True,
            "message": "连接成功",
            "version": version,
            "latency_ms": int((time.monotonic() - started) * 1000),
        }

    async def reindex(self, db: AsyncSession) -> dict:
        """从数据库重建索引（真实读写）

        **只索引当前站点可见的文章** —— 与前台 ``_published_stmt()`` 的口径逐条对齐：
        已发布 + 未隐藏 + 定时发布时间已到。索引里躺着不该被搜到的文档，
        再靠查询侧过滤是"二次补救"，不如一开始就不写进去。
        """
        config = await self.get_config(db)
        if not config["host"]:
            return {"ok": False, "message": "尚未配置 Meilisearch 地址", "indexed": 0, "skipped": 0}

        stmt = select(Article).where(
            Article.status == STATUS_PUBLISHED,
            Article.hidden.is_(False),
            or_(
                Article.scheduled_publish_at.is_(None),
                Article.scheduled_publish_at <= _now(),
            ),
        )
        stmt = apply_site_scope(stmt, Article)
        rows = (await db.execute(stmt)).scalars().all()

        documents = [_to_document(row) for row in rows]
        ok = await meilisearch_service.bulk_index_articles(documents)
        if not ok:
            return {
                "ok": False,
                "message": "写入索引失败，请检查连接配置与 Meilisearch 服务状态",
                "indexed": 0,
                "skipped": 0,
            }
        logger.info("Meilisearch 重建索引完成：%s 篇", len(documents))
        return {"ok": True, "message": f"已重建索引，共 {len(documents)} 篇", "indexed": len(documents), "skipped": 0}

    async def stats(self, db: AsyncSession) -> dict:
        """索引统计（引擎不可用时 available=False，**不报 0 冒充空索引**）"""
        config = await self.get_config(db)
        if not config["host"]:
            return {"ok": True, "available": False, "message": "尚未配置 Meilisearch 地址",
                    "index_name": config["index_name"], "documents": 0, "is_indexing": False}
        try:
            info = await meilisearch_service.get_index_stats()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "available": False, "message": f"读取索引统计失败：{type(exc).__name__}",
                    "index_name": config["index_name"], "documents": 0, "is_indexing": False}
        return {
            "ok": True,
            "available": True,
            "message": "",
            "index_name": config["index_name"],
            "documents": int((info or {}).get("number_of_documents") or 0),
            "is_indexing": bool((info or {}).get("is_indexing")),
        }

    async def load_into_service(self, db: AsyncSession) -> bool:
        """把生效配置推给服务单例（应用启动时调用一次）

        用内部的 ``_read_raw`` 而非脱敏的 ``get_config`` —— 这里需要**真实 api_key**
        才能建连，而 `get_config` 按设计不回显密钥。

        **不抛异常**：配置写坏、库连不上都不该阻断启动 —— 搜索是增强能力，
        不是启动依赖；失败就保持"未配置"，搜索自动走数据库回退。
        """
        try:
            raw = await self._read_raw(db)
            effective = _normalize(raw, fallback=env_config())
            meilisearch_service.configure(
                host=effective["host"],
                api_key=effective["api_key"],
                index_name=effective["index_name"],
                enabled=effective["enabled"],
            )
        except Exception as exc:  # noqa: BLE001 - 载入失败不影响启动
            logger.warning("Meilisearch 配置载入失败（搜索将回退数据库）：%s", exc)
            return False
        return meilisearch_service.is_configured()


def _now():
    """独立成函数便于测试替换（与 `article/service.py` 的写法一致）"""
    from datetime import datetime

    return datetime.now()


def _to_document(article: Any) -> dict:
    """把文章行转成索引文档（**纯函数**）

    字段与 `meilisearch_service._configure_index` 的 searchable/displayed 声明对应。
    可见性字段（`hidden` / `site_id` / `scheduled_publish_at` / `is_vip_only`）**必须**
    一起写入 —— 它们要在查询侧作为过滤条件使用（见 S4）。
    """
    return {
        "id": article.id,
        "title": article.title or "",
        "slug": article.slug or "",
        "excerpt": article.excerpt or "",
        "content": article.content or "",
        "cover_image": article.cover_image,
        "category_id": article.category,
        "category_name": getattr(article, "category_name", None),
        "author_id": article.user,
        "author_name": getattr(article, "author_name", None),
        "tags": article.tags_list or [],
        "views": int(article.views or 0),
        "likes": int(getattr(article, "likes", 0) or 0),
        "status": article.status,
        # 可见性字段：查询侧过滤要用，缺了就只能"事后补救"
        "hidden": bool(article.hidden),
        "is_vip_only": bool(article.is_vip_only),
        "required_vip_level": int(article.required_vip_level or 0),
        "site_id": article.site_id,
        "scheduled_publish_at": (
            int(article.scheduled_publish_at.timestamp())
            if article.scheduled_publish_at
            else None
        ),
        "is_featured": bool(article.is_featured),
        "created_at": int(article.created_at.timestamp()) if article.created_at else 0,
        "updated_at": int(article.updated_at.timestamp()) if article.updated_at else 0,
    }


search_settings_service = SearchSettingsService()
