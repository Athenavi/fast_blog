"""follow 模块路由（前台用户端：关注关系 / fans）

::

    GET    /api/v3/mobile/follow/follower            我的粉丝（分页）
    GET    /api/v3/mobile/follow/following           我的关注（分页）
    GET    /api/v3/mobile/follow/{user_id}/status    某人的关注概览（公开）
    GET    /api/v3/mobile/follow/{user_id}/follower  某人的粉丝（公开）
    GET    /api/v3/mobile/follow/{user_id}/following 某人的关注（公开）
    POST   /api/v3/mobile/follow/{user_id}           关注（仅认证）
    DELETE /api/v3/mobile/follow/{user_id}           取消关注（仅认证）

鉴权：

  - 「我的」两个列表与关注 / 取关：**仅需认证**（写操作已登记进 `audit.EXEMPT_WRITE_ENDPOINTS`：
    只操作本人数据，且目标用户存在性与拉黑关系在 service 层校验）；
  - 「某人的」三个只读端点：**公开**（`OptionalUser`）—— 登录时会额外带上
    `is_following` / `is_mutual` 标记，匿名则恒为 `false`。

> ⚠️ 静态段（`/follower`、`/following`）必须注册在 `/{user_id}` 之前，
> 否则会被参数路径吞掉（由 `assert_no_shadowed_routes` 在启动期强制）。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession, OptionalUser
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.mobile.follow.service import follow_service

router = APIRouter(prefix="/follow", tags=["mobile-follow"], route_class=OperationLogRoute)


@router.get("/follower", response_model=ResponseModel, summary="我的粉丝")
async def my_followers(
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await follow_service.follower_list(
        db, owner_id=current.id, viewer_id=current.id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/following", response_model=ResponseModel, summary="我的关注")
async def my_following(
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await follow_service.following_list(
        db, owner_id=current.id, viewer_id=current.id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/{user_id}/status", response_model=ResponseModel, summary="某人的关注概览")
async def follow_status(
    user_id: int,
    db: DBSession,
    viewer: OptionalUser,
) -> dict:
    return resp.success(
        await follow_service.stats(db, user_id, viewer.id if viewer is not None else None)
    )


@router.get("/{user_id}/follower", response_model=ResponseModel, summary="某人的粉丝")
async def user_followers(
    user_id: int,
    db: DBSession,
    viewer: OptionalUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await follow_service.follower_list(
        db,
        owner_id=user_id,
        viewer_id=viewer.id if viewer is not None else None,
        page=page,
        page_size=page_size,
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/{user_id}/following", response_model=ResponseModel, summary="某人的关注")
async def user_following(
    user_id: int,
    db: DBSession,
    viewer: OptionalUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await follow_service.following_list(
        db,
        owner_id=user_id,
        viewer_id=viewer.id if viewer is not None else None,
        page=page,
        page_size=page_size,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/{user_id}", response_model=ResponseModel, summary="关注")
async def follow_user(
    user_id: int,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    """幂等：已关注时直接返回当前概览；不能关注自己；对方拉黑我时 409"""
    return resp.success(await follow_service.follow(db, user_id, current.id), msg="关注成功")


@router.delete("/{user_id}", response_model=ResponseModel, summary="取消关注")
async def unfollow_user(
    user_id: int,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    """幂等：未关注过也返回成功"""
    return resp.success(await follow_service.unfollow(db, user_id, current.id), msg="已取消关注")
