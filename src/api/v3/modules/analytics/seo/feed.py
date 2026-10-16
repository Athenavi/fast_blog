"""RSS 2.0 / Atom 1.0 订阅路由

挂载点：``/api/v3/analytics/seo/feed/rss`` 与 ``/feed/atom``
（由 ``controller.py`` 以 ``/feed`` 前缀挂入 seo 模块）。

根路径 ``/rss.xml``、``/feed.xml``、``/atom.xml`` 由 ``src/app.py`` 301 过来，
与 sitemap 的约定一致。

公开路由：订阅源由阅读器与爬虫直接访问，无需鉴权；XML 直接响应（无统一 envelope）。
"""

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.advanced_features.feed_service import (
    generate_atom_feed,
    generate_rss_feed,
)
from src.api.v3.core.logger import get_logger
from src.utils.database.unified_manager import get_db_session

logger = get_logger("seo.feed")

router = APIRouter(tags=["seo-feed"])

_CACHE_FEED = {'Cache-Control': 'public, max-age=600'}


def _site_url(request: Request) -> str:
    return str(request.base_url).rstrip('/')


def _feed_response(content: str, media_type: str) -> Response:
    if not content:
        # 生成失败：明确返回 503，避免把空内容当作合法订阅源缓存
        return Response(status_code=503, content="feed unavailable", media_type="text/plain")
    return Response(content=content, media_type=media_type, headers=_CACHE_FEED)


@router.get("/rss", summary="RSS 2.0 订阅")
async def rss_feed(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100, description="条目数上限"),
    category_id: int | None = Query(default=None, description="仅输出该分类的文章"),
) -> Response:
    xml = await generate_rss_feed(
        db, base_url=_site_url(request), limit=limit, category_id=category_id
    )
    return _feed_response(xml, "application/rss+xml; charset=utf-8")


@router.get("/atom", summary="Atom 1.0 订阅")
async def atom_feed(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100, description="条目数上限"),
    category_id: int | None = Query(default=None, description="仅输出该分类的文章"),
) -> Response:
    xml = await generate_atom_feed(
        db, base_url=_site_url(request), limit=limit, category_id=category_id
    )
    return _feed_response(xml, "application/atom+xml; charset=utf-8")
