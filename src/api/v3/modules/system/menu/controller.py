"""menu 模块路由

RESTful 主路径::

    GET    /api/v3/system/menu                       菜单列表（含菜单项树）
    POST   /api/v3/system/menu                       新建菜单
    GET    /api/v3/system/menu/tree                  菜单项树（供动态路由）
    GET    /api/v3/system/menu/{menu_id}             菜单详情
    PUT    /api/v3/system/menu/{menu_id}             更新菜单
    DELETE /api/v3/system/menu/{menu_id}             删除菜单（连带菜单项）
    POST   /api/v3/system/menu/{menu_id}/items       新增菜单项
    PUT    /api/v3/system/menu/{menu_id}/items/order 重排菜单项
    PUT    /api/v3/system/menu/items/{item_id}       更新菜单项
    DELETE /api/v3/system/menu/items/{item_id}       删除菜单项

静态路径（``/tree``、``/items/{item_id}``）必须注册在 ``/{menu_id}`` 之前
（``assert_no_shadowed_routes`` 会强制）。

权限码：``menu:view`` / ``menu:create`` / ``menu:edit`` / ``menu:delete``
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.menu.schema import (
    MenuCreate,
    MenuItemCreate,
    MenuItemOrderRequest,
    MenuItemUpdate,
    MenuUpdate,
)
from src.api.v3.modules.system.menu.service import menu_service

router = APIRouter(prefix="/menu", tags=["system-menu"], route_class=OperationLogRoute)


# ─────────────────────────── 列表 / 树（静态路径优先）───────────────────────────
@router.get("", response_model=ResponseModel, summary="菜单列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 菜单列表",
)
async def list_menus(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_VIEW),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    menus = await menu_service.list_menus(db, is_active=is_active)
    return resp.success_page(menus, len(menus), 1, len(menus) or 1)


@router.get("/tree", response_model=ResponseModel, summary="菜单项树")
async def menu_tree(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_VIEW),
    menu_id: Optional[int] = Query(default=None, description="留空返回全部菜单的树"),
) -> dict:
    return resp.success(await menu_service.tree(db, menu_id))


# ─────────────────────────── 新建 ───────────────────────────
@router.post("", response_model=ResponseModel, summary="创建菜单")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 创建菜单",
)
async def create_menu(
    payload: MenuCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_CREATE),
) -> dict:
    return resp.success(await menu_service.create_menu(db, payload), msg="创建成功")


# ─────────────────────────── 菜单项（静态路径必须早于 /{menu_id}）───────────
@router.put("/items/{item_id}", response_model=ResponseModel, summary="更新菜单项")
async def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_EDIT),
) -> dict:
    return resp.success(await menu_service.update_item(db, item_id, payload), msg="更新成功")


@router.delete("/items/{item_id}", response_model=ResponseModel, summary="删除菜单项")
async def delete_menu_item(
    item_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_DELETE),
) -> dict:
    await menu_service.delete_item(db, item_id)
    return resp.success(None, msg="已删除")


# ─────────────────────────── 详情 / 更新 / 删除 ───────────────────────────
@router.get("/{menu_id}", response_model=ResponseModel, summary="菜单详情")
async def get_menu(
    menu_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_VIEW),
) -> dict:
    return resp.success(await menu_service.get_menu(db, menu_id))


@router.put("/{menu_id}", response_model=ResponseModel, summary="更新菜单")
@router.put(
    "/update/{menu_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新菜单",
)
async def update_menu(
    menu_id: int,
    payload: MenuUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_EDIT),
) -> dict:
    return resp.success(await menu_service.update_menu(db, menu_id, payload), msg="更新成功")


@router.delete("/{menu_id}", response_model=ResponseModel, summary="删除菜单")
async def delete_menu(
    menu_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_DELETE),
) -> dict:
    await menu_service.delete_menu(db, menu_id)
    return resp.success(None, msg="已删除")


@router.post("/{menu_id}/items", response_model=ResponseModel, summary="新增菜单项")
async def add_menu_item(
    menu_id: int,
    payload: MenuItemCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_CREATE),
) -> dict:
    return resp.success(await menu_service.add_item(db, menu_id, payload), msg="创建成功")


@router.put("/{menu_id}/items/order", response_model=ResponseModel, summary="重排菜单项")
async def reorder_menu_items(
    menu_id: int,
    payload: MenuItemOrderRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NAVMENU_EDIT),
) -> dict:
    order = [(item.id, item.order_index) for item in payload.items]
    return resp.success(await menu_service.reorder_items(db, menu_id, order), msg="排序已更新")
