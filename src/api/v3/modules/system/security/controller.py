"""security 模块路由（T5-11 批次 3：自 astro `admin/security` 能力域新建）

::

    GET    /api/v3/system/security/overview              安全总览（24h 尝试/失败/锁定/黑名单）
    GET    /api/v3/system/security/attempts              登录尝试列表
    GET    /api/v3/system/security/blacklist             令牌黑名单列表
    DELETE /api/v3/system/security/blacklist/{entry_id}  删除黑名单记录

权限码：``module_system:security:view/delete``。
锁定账户管理已在 ``system/log``（lockouts / users history）覆盖，此处不重复。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.security.service import security_service

router = APIRouter(prefix="/security", tags=["system-security"], route_class=OperationLogRoute)


@router.get("/overview", response_model=ResponseModel, summary="安全总览")
async def overview(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
) -> dict:
    return resp.success(await security_service.overview(db))


@router.get("/attempts", response_model=ResponseModel, summary="登录尝试列表")
async def list_attempts(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    username: Optional[str] = Query(default=None),
    is_success: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await security_service.list_attempts(
        db, page=page, page_size=page_size, username=username, is_success=is_success
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/blacklist", response_model=ResponseModel, summary="令牌黑名单")
async def list_blacklist(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await security_service.list_blacklist(db, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)


@router.delete("/blacklist/{entry_id}", response_model=ResponseModel, summary="删除黑名单记录")
async def delete_blacklist(
    entry_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_DELETE),
) -> dict:
    await security_service.delete_blacklist(db, entry_id)
    return resp.success(None, msg="已删除")
