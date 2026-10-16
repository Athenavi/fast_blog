"""group 模块路由

RESTful 主路径 + FastApiAdmin 兼容别名::

    GET    /api/v3/system/group                        权限组列表
    GET    /api/v3/system/group/tree                   权限组树
    POST   /api/v3/system/group                        新建权限组
    DELETE /api/v3/system/group/delete                 [兼容] 删除
    GET    /api/v3/system/group/{group_id}             详情
    PUT    /api/v3/system/group/{group_id}             更新
    DELETE /api/v3/system/group/{group_id}             删除
    GET    /api/v3/system/group/{group_id}/members     成员列表
    POST   /api/v3/system/group/{group_id}/members     全量覆盖成员
    DELETE /api/v3/system/group/{group_id}/members/{user_id}  移出成员
    GET    /api/v3/system/group/{group_id}/roles       绑定角色
    PUT    /api/v3/system/group/{group_id}/roles       全量覆盖绑定角色

静态路径（``/tree``、``/list``、``/create``、``/delete``）必须早于 ``/{group_id}``。

权限码：``group:view`` / ``group:*``（见 ``core/permission/codes.py``）。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.group.schema import (
    GroupMemberAssign,
    GroupRoleAssign,
    PermissionGroupCreate,
    PermissionGroupUpdate,
)
from src.api.v3.modules.system.group.service import group_service

router = APIRouter(prefix="/group", tags=["system-group"], route_class=OperationLogRoute)


# ─────────────────────────── 列表 / 树（静态路径优先）───────────────────────────
@router.get("", response_model=ResponseModel, summary="权限组列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 权限组列表",
)
async def list_groups(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_VIEW),
    is_active: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
) -> dict:
    groups = await group_service.list_groups(db, is_active=is_active, keyword=keyword)
    return resp.success_page(groups, len(groups), 1, len(groups) or 1)


@router.get("/tree", response_model=ResponseModel, summary="权限组树")
async def group_tree(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_VIEW),
    is_active: bool | None = Query(default=None),
) -> dict:
    return resp.success(await group_service.tree(db, is_active=is_active))


# ─────────────────────────── 新建 ───────────────────────────
@router.post("", response_model=ResponseModel, summary="新建权限组")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 新建权限组",
)
async def create_group(
    payload: PermissionGroupCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_CREATE),
) -> dict:
    return resp.success(await group_service.create_group(db, payload), msg="创建成功")


@router.delete(
    "/delete",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 删除权限组",
)
async def delete_group_compat(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_DELETE),
    group_id: int = Query(description="待删除的权限组 id"),
) -> dict:
    await group_service.delete_group(db, group_id)
    return resp.success(None, msg="已删除")


# ─────────────────────────── 详情 / 更新 / 删除 ───────────────────────────
@router.get("/{group_id}", response_model=ResponseModel, summary="权限组详情")
@router.get(
    "/detail/{group_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 权限组详情",
)
async def get_group(
    group_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_VIEW),
) -> dict:
    return resp.success(await group_service.get_group_out(db, group_id))


@router.put("/{group_id}", response_model=ResponseModel, summary="更新权限组")
@router.put(
    "/update/{group_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新权限组",
)
async def update_group(
    group_id: int,
    payload: PermissionGroupUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_EDIT),
) -> dict:
    return resp.success(await group_service.update_group(db, group_id, payload), msg="更新成功")


@router.delete("/{group_id}", response_model=ResponseModel, summary="删除权限组")
async def delete_group(
    group_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_DELETE),
) -> dict:
    await group_service.delete_group(db, group_id)
    return resp.success(None, msg="已删除")


# ─────────────────────────── 成员 ───────────────────────────
@router.get("/{group_id}/members", response_model=ResponseModel, summary="组成员列表")
async def list_members(
    group_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_VIEW),
) -> dict:
    members = await group_service.list_members(db, group_id)
    return resp.success_page(members, len(members), 1, len(members) or 1)


@router.post("/{group_id}/members", response_model=ResponseModel, summary="全量覆盖组成员")
async def set_members(
    group_id: int,
    payload: GroupMemberAssign,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_MANAGE_MEMBERS),
) -> dict:
    members = await group_service.set_members(db, group_id, payload.user_ids)
    return resp.success(members, msg="成员已更新")


@router.delete("/{group_id}/members/{user_id}", response_model=ResponseModel, summary="移出成员")
async def remove_member(
    group_id: int,
    user_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_MANAGE_MEMBERS),
) -> dict:
    await group_service.remove_member(db, group_id, user_id)
    return resp.success(None, msg="已移出")


# ─────────────────────────── 角色绑定 ───────────────────────────
@router.get("/{group_id}/roles", response_model=ResponseModel, summary="组绑定的角色")
async def list_group_roles(
    group_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_VIEW),
) -> dict:
    return resp.success(await group_service.list_roles(db, group_id))


@router.put("/{group_id}/roles", response_model=ResponseModel, summary="全量覆盖组绑定的角色")
async def set_group_roles(
    group_id: int,
    payload: GroupRoleAssign,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GROUP_MANAGE_ROLES),
) -> dict:
    roles = await group_service.set_roles(db, group_id, payload.role_ids)
    return resp.success(roles, msg="绑定已更新")
