"""user 模块路由

**主路径（RESTful）**::

    GET    /api/v3/system/user            列表
    POST   /api/v3/system/user            新建
    GET    /api/v3/system/user/{user_id}  详情
    PUT    /api/v3/system/user/{user_id}  更新
    DELETE /api/v3/system/user/{user_id}  删除（默认停用，?force=true 物理删除）
    POST   /api/v3/system/user/{user_id}/status     启用/停用
    GET    /api/v3/system/user/{user_id}/roles      用户角色
    POST   /api/v3/system/user/{user_id}/roles      分配角色
    GET    /api/v3/system/user/{user_id}/permissions 用户权限码

**FastApiAdmin 兼容别名**（``include_in_schema=False``）：``/list``、``/detail/{id}``、
``/create``、``/update/{id}``、``/delete``，便于官方前端/文档直接对接。

兼容别名是**静态路径**，必须注册在 ``/{user_id}`` 之前，否则会被路径参数吞掉 ——
``core/discover.py`` 的 ``assert_no_shadowed_routes`` 会在启动期强制这一点
（该缺陷在本项目旧 v3 真实发生过）。注意 Python 装饰器自下而上执行，
因此别名装饰器写在同组的最下方。

权限码：``user:view`` / ``user:create`` / ``user:edit`` / ``user:delete`` / ``user:manage_roles``
"""

from typing import List, Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.user.schema import (
    RoleAssignRequest,
    UserCreate,
    UserOut,
    UserStatusUpdate,
    UserUpdate,
)
from src.api.v3.modules.system.user.service import user_service

router = APIRouter(
    prefix="/user", tags=["system-user"], route_class=OperationLogRoute
)


def _out(user) -> dict:
    return UserOut.model_validate(user).model_dump()


# ─────────────────────────── 列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="用户列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 用户列表",
)
async def list_users(
    page: PageDep,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:view"),
    is_active: Optional[bool] = Query(default=None, description="按启用状态过滤"),
    is_superuser: Optional[bool] = Query(default=None, description="按超管标记过滤"),
) -> dict:
    items, total = await user_service.list_users(
        db,
        page=page.page,
        page_size=page.page_size,
        keyword=page.keyword,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    return resp.success_page([_out(user) for user in items], total, page.page, page.page_size)


# ─────────────────────────── 新建 ───────────────────────────
@router.post("", response_model=ResponseModel, summary="创建用户")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 创建用户",
)
async def create_user(
    payload: UserCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:create"),
) -> dict:
    user = await user_service.create_user(db, payload)
    return resp.success(_out(user), msg="创建成功")


# ─────────────────────────── 兼容删除（官方为 DELETE /delete，id 走请求）────────
@router.delete(
    "/delete",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 删除用户",
)
async def delete_users_compat(
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl("user:delete"),
    ids: List[int] = Query(default=[], description="待删除的用户 id 列表"),
    force: bool = Query(default=False, description="true=物理删除"),
) -> dict:
    if not ids:
        raise BadRequestError("缺少 ids 参数")
    for user_id in ids:
        await user_service.delete_user(db, user_id, current.id, force=force)
    return resp.success({"count": len(ids)}, msg="处理完成")


# ─────────────────────────── 详情 ───────────────────────────
@router.get("/{user_id}", response_model=ResponseModel, summary="用户详情")
@router.get(
    "/detail/{user_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 用户详情",
)
async def get_user(
    user_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:view"),
) -> dict:
    user = await user_service.get_user(db, user_id)
    return resp.success(_out(user))


# ─────────────────────────── 更新 ───────────────────────────
@router.put("/{user_id}", response_model=ResponseModel, summary="更新用户")
@router.put(
    "/update/{user_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新用户",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:edit"),
) -> dict:
    user = await user_service.update_user(db, user_id, payload)
    return resp.success(_out(user), msg="更新成功")


# ─────────────────────────── 删除（默认停用）───────────────────────────
@router.delete("/{user_id}", response_model=ResponseModel, summary="删除用户（默认停用）")
async def delete_user(
    user_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl("user:delete"),
    force: bool = Query(default=False, description="true=物理删除；默认仅停用"),
) -> dict:
    await user_service.delete_user(db, user_id, current.id, force=force)
    return resp.success(None, msg="已删除" if force else "已停用")


# ─────────────────────────── 状态 ───────────────────────────
@router.post("/{user_id}/status", response_model=ResponseModel, summary="启用 / 停用用户")
async def set_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:edit"),
) -> dict:
    user = await user_service.set_status(db, user_id, payload.is_active)
    return resp.success(_out(user), msg="已启用" if payload.is_active else "已停用")


# ─────────────────────────── 角色 ───────────────────────────
@router.get("/{user_id}/roles", response_model=ResponseModel, summary="用户角色")
async def get_user_roles(
    user_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:view"),
) -> dict:
    return resp.success(await user_service.get_user_roles(db, user_id))


@router.post("/{user_id}/roles", response_model=ResponseModel, summary="分配用户角色")
async def set_user_roles(
    user_id: int,
    payload: RoleAssignRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:manage_roles"),
) -> dict:
    roles = await user_service.set_user_roles(db, user_id, payload.role_ids)
    return resp.success(roles, msg="角色已更新")


@router.get("/{user_id}/permissions", response_model=ResponseModel, summary="用户权限码")
async def get_user_permissions(
    user_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("user:view"),
) -> dict:
    return resp.success(await user_service.get_user_permissions(db, user_id))
