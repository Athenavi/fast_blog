"""mobile/user 路由

::

    GET /api/v3/mobile/user/profile          我的资料（需登录）
    PUT /api/v3/mobile/user/profile          修改资料（需登录，白名单字段）
    GET /api/v3/mobile/user/stats            我的统计（需登录）
    GET /api/v3/mobile/user/public/{username} 用户公开主页（公开；登录时带关注标记）

> ⚠️ 静态段（``/profile``、``/stats``）必须先于任何可吞掉它们的动态段注册；
> ``/public/{username}`` 为两段静态前缀，与它们互不遮蔽。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession, OptionalUser
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.mobile.user.schema import MobileProfileUpdate
from src.api.v3.modules.mobile.user.service import mobile_user_service

router = APIRouter(prefix="/user", tags=["mobile-user"], route_class=OperationLogRoute)


@router.get("/profile", response_model=ResponseModel, summary="我的资料")
async def get_profile(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await mobile_user_service.profile(db, current))


@router.put("/profile", response_model=ResponseModel, summary="修改我的资料")
async def update_profile(
    payload: MobileProfileUpdate,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    return resp.success(await mobile_user_service.update_profile(db, current, payload), msg="已保存")


@router.get("/stats", response_model=ResponseModel, summary="我的统计")
async def get_stats(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await mobile_user_service.stats(db, current.id))


@router.get("/public/{username}", response_model=ResponseModel, summary="用户公开主页")
async def get_public_profile(
    username: str,
    db: DBSession,
    viewer: OptionalUser,
) -> dict:
    """公开端点（``OptionalUser``）：匿名可访问；登录时额外给出
    ``is_following`` / ``is_mutual``（viewer 与目标为同一人时恒为 false）。

    用户不存在或未激活 → 404；``profile_private`` 为真时只回 id / username /
    profile_picture，绝不泄露 ``bio`` 与统计。
    """
    return resp.success(
        await mobile_user_service.public_profile(
            db, username, viewer.id if viewer is not None else None
        )
    )
