"""admin_menu 模块路由

RESTful 主路径 + 兼容别名::

    GET    /api/v3/system/admin-menu                  菜单列表
    GET    /api/v3/system/admin-menu/tree             菜单树
    GET    /api/v3/system/admin-menu/my               当前用户可见菜单标识
    POST   /api/v3/system/admin-menu                  新建菜单
    DELETE /api/v3/system/admin-menu/delete           [兼容] 删除
    GET    /api/v3/system/admin-menu/role/{role_id}   角色已授权菜单 id
    PUT    /api/v3/system/admin-menu/role/{role_id}   全量覆盖角色菜单授权
    GET    /api/v3/system/admin-menu/{menu_id}        菜单详情
    PUT    /api/v3/system/admin-menu/{menu_id}        更新菜单
    DELETE /api/v3/system/admin-menu/{menu_id}        删除菜单

**单段静态路径（``/list``、``/tree``、``/my``、``/create``、``/delete``）必须早于 ``/{menu_id}``**，
否则 ``/my`` 会被当成 ``menu_id="my"``。

权限码：``ADMIN_MENU_*``（见 ``core/permission/codes.py``，当前映射到 ``settings:*``）。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.admin_menu.schema import (
    AdminMenuCreate,
    AdminMenuUpdate,
    RoleMenuAssign,
)
from src.api.v3.modules.system.admin_menu.service import admin_menu_service

router = APIRouter(prefix="/admin-menu", tags=["system-admin-menu"], route_class=OperationLogRoute)


# ─────────────────────────── 列表 / 树 / 我的（静态路径优先）───────────────────────────
@router.get("", response_model=ResponseModel, summary="后台菜单列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 后台菜单列表",
)
async def list_menus(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MENU_VIEW),
    is_active: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
) -> dict:
    menus = await admin_menu_service.list_menus(db, is_active=is_active, keyword=keyword)
    return resp.success_page(menus, len(menus), 1, len(menus) or 1)


@router.get("/tree", response_model=ResponseModel, summary="后台菜单树")
async def menu_tree(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MENU_VIEW),
    is_active: bool | None = Query(default=None),
) -> dict:
    return resp.success(await admin_menu_service.tree(db, is_active=is_active))


@router.get("/my", response_model=ResponseModel, summary="当前用户可见菜单标识")
async def my_menus(db: DBSession, current: CurrentUser) -> dict:
    menu_codes = await admin_menu_service.menu_codes_with_ancestors(
        db, current.id, is_superuser=bool(getattr(current, "is_superuser", False))
    )
    return resp.success(
        {"menu_codes": menu_codes, "is_superuser": bool(getattr(current, "is_superuser", False))}
    )


# ─────────────────────────── 新建 / 兼容删除 ───────────────────────────
@router.post("", response_model=ResponseModel, summary="新建后台菜单")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 新建后台菜单",
)
async def create_menu(
    payload: AdminMenuCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MENU_CREATE),
) -> dict:
    return resp.success(await admin_menu_service.create_menu(db, payload), msg="创建成功")


@router.delete(
    "/delete",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 删除后台菜单",
)
async def delete_menu_compat(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MENU_DELETE),
    menu_id: int = Query(description="待删除的菜单 id"),
) -> dict:
    await admin_menu_service.delete_menu(db, menu_id)
    return resp.success(None, msg="已删除")


# ─────────────────────────── 角色授权 ───────────────────────────
@router.get("/role/{role_id}", response_model=ResponseModel, summary="角色已授权的菜单 id")
async def role_menus(
    role_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MENU_VIEW),
) -> dict:
    return resp.success(await admin_menu_service.menu_ids_of_role(db, role_id))


@router.put("/role/{role_id}", response_model=ResponseModel, summary="全量覆盖角色菜单授权")
async def set_role_menus(
    role_id: int,
    payload: RoleMenuAssign,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MENU_GRANT),
) -> dict:
    menu_ids = await admin_menu_service.set_role_menus(db, role_id, payload.menu_ids)
    return resp.success(menu_ids, msg="授权已更新")


# ─────────────────────────── 详情 / 更新 / 删除 ───────────────────────────
@router.get("/{menu_id}", response_model=ResponseModel, summary="后台菜单详情")
@router.get(
    "/detail/{menu_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 后台菜单详情",
)
async def get_menu(
    menu_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MENU_VIEW),
) -> dict:
    return resp.success(await admin_menu_service.get_menu_out(db, menu_id))


@router.put("/{menu_id}", response_model=ResponseModel, summary="更新后台菜单")
@router.put(
    "/update/{menu_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新后台菜单",
)
async def update_menu(
    menu_id: int,
    payload: AdminMenuUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MENU_EDIT),
) -> dict:
    return resp.success(await admin_menu_service.update_menu(db, menu_id, payload), msg="更新成功")


@router.delete("/{menu_id}", response_model=ResponseModel, summary="删除后台菜单")
async def delete_menu(
    menu_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MENU_DELETE),
) -> dict:
    await admin_menu_service.delete_menu(db, menu_id)
    return resp.success(None, msg="已删除")
