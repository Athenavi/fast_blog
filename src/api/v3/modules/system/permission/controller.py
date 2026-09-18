"""permission 模块路由

RESTful 主路径::

    GET  /api/v3/system/permission                权限码列表
    GET  /api/v3/system/permission/grouped        按资源分组的权限码
    GET  /api/v3/system/permission/my             当前用户权限码
    POST /api/v3/system/permission/check          批量校验权限码
    GET  /api/v3/system/permission/cache-stats    权限缓存统计
    POST /api/v3/system/permission/cache/invalidate  失效权限缓存

兼容别名：``/capabilities``（等同 ``/permission``）。

权限码：列表 → ``user:view``；自身权限 → 仅需登录；缓存操作 → ``settings:view`` / ``settings:edit``。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.modules.system.permission.schema import (
    CapabilityOut,
    PermissionCheckRequest,
)
from src.api.v3.modules.system.permission.service import permission_service

router = APIRouter(prefix="/permission", tags=["system-permission"])


# ─────────────────────────── 权限码列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="权限码列表")
@router.get(
    "/capabilities",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容别名] 权限码列表",
)
async def list_capabilities(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PERMISSION_VIEW),
    resource_type: Optional[str] = Query(default=None, description="按资源类型过滤，如 article"),
    keyword: Optional[str] = Query(default=None, description="按 code/name 模糊搜索"),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    caps, total = await permission_service.list_capabilities(
        db, resource_type=resource_type, keyword=keyword, is_active=is_active
    )
    return resp.success_page(
        [CapabilityOut.model_validate(cap).model_dump() for cap in caps], total, 1, len(caps) or 1
    )


@router.get("/grouped", response_model=ResponseModel, summary="按资源分组的权限码")
async def grouped_capabilities(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PERMISSION_VIEW),
) -> dict:
    return resp.success(await permission_service.grouped(db))


# ─────────────────────────── 当前用户权限 ───────────────────────────
@router.get("/my", response_model=ResponseModel, summary="当前用户权限码")
async def my_permissions(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await permission_service.user_permissions(db, current.id))


@router.post("/check", response_model=ResponseModel, summary="批量校验权限码")
async def check_permissions(
    payload: PermissionCheckRequest,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    return resp.success(await permission_service.check(db, current.id, payload.codes))


# ─────────────────────────── 权限缓存 ───────────────────────────
@router.get("/cache-stats", response_model=ResponseModel, summary="权限缓存统计")
async def cache_stats(
    _current: CurrentUser,
    _perm=AuthControl(codes.PERMISSION_VIEW),
) -> dict:
    return resp.success(await permission_service.cache_stats())


@router.post("/cache/invalidate", response_model=ResponseModel, summary="失效权限缓存")
async def invalidate_cache(
    _current: CurrentUser,
    _perm=AuthControl(codes.PERMISSION_EDIT),
    user_id: Optional[int] = Query(default=None, description="留空表示清空全部缓存"),
) -> dict:
    await permission_service.invalidate_cache(user_id)
    return resp.success(None, msg="缓存已失效")
