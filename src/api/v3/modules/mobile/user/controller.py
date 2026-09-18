"""mobile/user 路由

::

    GET /api/v3/mobile/user/profile   我的资料（需登录）
    PUT /api/v3/mobile/user/profile   修改资料（需登录，白名单字段）
    GET /api/v3/mobile/user/stats     我的统计（需登录）
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession
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
