"""role 模块路由

RESTful 主路径::

    GET    /api/v3/system/role                        角色列表
    POST   /api/v3/system/role                        新建角色
    GET    /api/v3/system/role/{role_id}              角色详情
    PUT    /api/v3/system/role/{role_id}              更新角色
    DELETE /api/v3/system/role/{role_id}              删除角色
    GET    /api/v3/system/role/{role_id}/permissions  角色权限码
    PUT    /api/v3/system/role/{role_id}/permissions  设置角色权限码

FastApiAdmin 兼容别名：``/list``、``/create``、``/detail/{id}``、``/update/{id}``、
``/delete``、``/permission/{id}``（GET/PUT）。

权限码：``user:manage_roles``（角色管理）；查询权限码清单用 ``user:view``。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.role.schema import (
    RoleCreate,
    RolePermissionsRequest,
    RoleUpdate,
)
from src.api.v3.modules.system.role.service import role_service

router = APIRouter(prefix="/role", tags=["system-role"], route_class=OperationLogRoute)


# ─────────────────────────── 列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="角色列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 角色列表",
)
async def list_roles(
    page: PageDep,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:manage_roles"),
    is_system: Optional[bool] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await role_service.list_roles(
        db,
        page=page.page,
        page_size=page.page_size,
        keyword=page.keyword,
        is_system=is_system,
        is_active=is_active,
    )
    return resp.success_page(items, total, page.page, page.page_size)


# ─────────────────────────── 新建 ───────────────────────────
@router.post("", response_model=ResponseModel, summary="创建角色")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 创建角色",
)
async def create_role(
    payload: RoleCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:manage_roles"),
) -> dict:
    return resp.success(await role_service.create_role(db, payload), msg="创建成功")


# ─────────────────────────── 兼容删除（静态路径必须在 /{role_id} 之前）──────────
@router.delete(
    "/delete",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 删除角色",
)
async def delete_role_compat(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:manage_roles"),
    role_id: int = Query(description="待删除角色 id"),
) -> dict:
    await role_service.delete_role(db, role_id)
    return resp.success(None, msg="已删除")


# ─────────────────────────── 兼容权限设置（静态路径）──────────
@router.get(
    "/permission/{role_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 角色权限码",
)
async def get_role_permissions_compat(
    role_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:view"),
) -> dict:
    return resp.success(await role_service.get_permissions(db, role_id))


@router.put(
    "/permission/{role_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 设置角色权限码",
)
async def set_role_permissions_compat(
    role_id: int,
    payload: RolePermissionsRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:manage_roles"),
) -> dict:
    codes = await role_service.set_permissions(db, role_id, payload.permission_codes)
    return resp.success(codes, msg="权限已更新")


# ─────────────────────────── 详情 / 更新 / 删除 ───────────────────────────
@router.get("/{role_id}", response_model=ResponseModel, summary="角色详情")
@router.get(
    "/detail/{role_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 角色详情",
)
async def get_role(
    role_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:manage_roles"),
) -> dict:
    return resp.success(await role_service.get_role_out(db, role_id))


@router.put("/{role_id}", response_model=ResponseModel, summary="更新角色")
@router.put(
    "/update/{role_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新角色",
)
async def update_role(
    role_id: int,
    payload: RoleUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:manage_roles"),
) -> dict:
    return resp.success(await role_service.update_role(db, role_id, payload), msg="更新成功")


@router.delete("/{role_id}", response_model=ResponseModel, summary="删除角色")
async def delete_role(
    role_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:manage_roles"),
) -> dict:
    await role_service.delete_role(db, role_id)
    return resp.success(None, msg="已删除")


@router.get("/{role_id}/permissions", response_model=ResponseModel, summary="角色权限码")
async def get_role_permissions(
    role_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:view"),
) -> dict:
    return resp.success(await role_service.get_permissions(db, role_id))


@router.put("/{role_id}/permissions", response_model=ResponseModel, summary="设置角色权限码")
async def set_role_permissions(
    role_id: int,
    payload: RolePermissionsRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:manage_roles"),
) -> dict:
    codes = await role_service.set_permissions(db, role_id, payload.permission_codes)
    return resp.success(codes, msg="权限已更新")
