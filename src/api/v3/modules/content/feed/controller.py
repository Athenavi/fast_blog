"""feed 模块路由（任务 13：动态流）

::

    GET /api/v3/content/feed/timeline        关注时间线（登录）
    GET /api/v3/content/feed/discover        发现流（公开）
    GET /api/v3/content/feed/user/{user_id}  某用户的公开动态（公开）
    GET /api/v3/content/feed/stats           我的流概览（登录）

关注 / 取关 / 粉丝列表在 ``mobile/follow``（已实现，真表 ``user_follows``）——
本模块只做「流」的聚合，不重复实现关注关系。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession, PageDep
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.feed.service import EVENT_TYPES, feed_service

router = APIRouter(prefix="/feed", tags=["content-feed"], route_class=OperationLogRoute)


@router.get("/timeline", response_model=ResponseModel, summary="关注时间线")
async def timeline(
    db: DBSession,
    current: CurrentUser,
    page: PageDep = None,
    event_types: Optional[str] = Query(
        default=None,
        description=f"逗号分隔，可选 {', '.join(EVENT_TYPES)}；留空=全部",
    ),
) -> dict:
    """关注的人产生的新文章 / 点赞 / 评论，按时间倒序；没关注任何人时返回空并给出提示"""
    parsed = tuple(item.strip() for item in event_types.split(",")) if event_types else None
    items, total = await feed_service.timeline(
        db, int(current.id), page=page.page, page_size=page.page_size, event_types=parsed
    )
    return resp.success_page(items, total, page.page, page.page_size)


@router.get("/discover", response_model=ResponseModel, summary="发现流（公开）")
async def discover(
    db: DBSession,
    page: PageDep = None,
    include_interactions: bool = Query(
        default=False, description="true 时把全站最新点赞 / 评论也纳入（默认只看新文章）"
    ),
) -> dict:
    items, total = await feed_service.discover(
        db,
        page=page.page,
        page_size=page.page_size,
        include_interactions=include_interactions,
    )
    return resp.success_page(items, total, page.page, page.page_size)


@router.get("/user/{user_id}", response_model=ResponseModel, summary="某用户的公开动态（公开）")
async def user_feed(
    user_id: int,
    db: DBSession,
    page: PageDep = None,
) -> dict:
    items, total = await feed_service.user_feed(
        db, user_id, page=page.page, page_size=page.page_size
    )
    return resp.success_page(items, total, page.page, page.page_size)


@router.get("/stats", response_model=ResponseModel, summary="我的流概览")
async def feed_stats(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await feed_service.stats(db, int(current.id)))
