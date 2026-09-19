"""social 模块路由（T5-11 批次 3：自 astro `admin/social` 能力域新建）

::

    GET    /api/v3/system/social/account                绑定列表（令牌脱敏）
    DELETE /api/v3/system/social/account/{account_id}   解除绑定

权限码：``module_system:social:view/delete``。
OAuth 登录流程本身由既有 auth 体系承担，本模块只做绑定档案管理。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.social.service import social_service

router = APIRouter(prefix="/social", tags=["system-social"], route_class=OperationLogRoute)


@router.get("/account", response_model=ResponseModel, summary="社交账号绑定列表")
async def list_accounts(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SOCIAL_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: Optional[int] = Query(default=None),
    provider: Optional[str] = Query(default=None),
) -> dict:
    items, total = await social_service.list_accounts(
        db, page=page, page_size=page_size, user_id=user_id, provider=provider
    )
    return resp.success_page(items, total, page, page_size)


@router.delete("/account/{account_id}", response_model=ResponseModel, summary="解除绑定")
async def delete_binding(
    account_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SOCIAL_DELETE),
) -> dict:
    await social_service.delete_binding(db, account_id)
    return resp.success(None, msg="已解除")
