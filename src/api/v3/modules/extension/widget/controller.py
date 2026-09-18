"""widget 模块路由

**公开（无鉴权，前台渲染用）**::

    GET /api/v3/extension/widget/public/area/{area}   某区域启用的部件

**管理端（需权限码）**::

    GET    /api/v3/extension/widget           部件列表
    GET    /api/v3/extension/widget/types     可用部件类型（只读元数据）
    GET    /api/v3/extension/widget/areas     可用区域（只读元数据）
    POST   /api/v3/extension/widget           新建部件
    POST   /api/v3/extension/widget/reorder   批量排序
    GET    /api/v3/extension/widget/{id}      部件详情
    PUT    /api/v3/extension/widget/{id}      更新部件
    PATCH  /api/v3/extension/widget/{id}/toggle  启用 / 停用
    DELETE /api/v3/extension/widget/{id}      删除部件

静态路径（``/types``、``/areas``、``/reorder``、``/public/*``）必须早于 ``/{widget_id}``。

权限码：``settings:view`` / ``settings:edit``
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.extension.widget.schema import (
    WidgetCreate,
    WidgetReorderRequest,
    WidgetToggleRequest,
    WidgetUpdate,
)
from src.api.v3.modules.extension.widget.service import widget_service

router = APIRouter(prefix="/widget", tags=["extension-widget"], route_class=OperationLogRoute)


# ─────────────────────────── 公开（无鉴权）───────────────────────────
@router.get(
    "/public/area/{area}",
    response_model=ResponseModel,
    summary="某区域启用的部件（无需鉴权）",
)
async def public_widgets_by_area(area: str, db: DBSession) -> dict:
    return resp.success(await widget_service.public_by_area(db, area))


# ─────────────────────────── 只读元数据（静态路径优先）───────────────────────────
@router.get("/types", response_model=ResponseModel, summary="可用部件类型")
async def widget_types(
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
) -> dict:
    return resp.success(await widget_service.widget_types())


@router.get("/areas", response_model=ResponseModel, summary="可用部件区域")
async def widget_areas(
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
) -> dict:
    return resp.success(await widget_service.widget_areas())


# ─────────────────────────── 批量排序（静态路径优先）───────────────────────────
@router.post("/reorder", response_model=ResponseModel, summary="批量排序")
async def reorder_widgets(
    payload: WidgetReorderRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    pairs = [(item.id, item.order_index) for item in payload.items]
    affected = await widget_service.reorder(db, pairs)
    return resp.success({"affected": affected}, msg="排序已更新")


# ─────────────────────────── 列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="部件列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 部件列表",
)
async def list_widgets(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
    area: str | None = None,
    widget_type: str | None = None,
    is_active: bool | None = None,
) -> dict:
    items = await widget_service.list_widgets(
        db, area=area, widget_type=widget_type, is_active=is_active
    )
    return resp.success_page(items, len(items), 1, len(items) or 1)


# ─────────────────────────── 新建 ───────────────────────────
@router.post("", response_model=ResponseModel, summary="创建部件")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 创建部件",
)
async def create_widget(
    payload: WidgetCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    return resp.success(await widget_service.create_widget(db, payload), msg="创建成功")


# ─────────────────────────── 详情 / 更新 / 切换 / 删除 ───────────────────────────
@router.get("/{widget_id}", response_model=ResponseModel, summary="部件详情")
async def get_widget(
    widget_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
) -> dict:
    return resp.success(await widget_service.get_widget(db, widget_id))


@router.put("/{widget_id}", response_model=ResponseModel, summary="更新部件")
@router.put(
    "/update/{widget_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新部件",
)
async def update_widget(
    widget_id: int,
    payload: WidgetUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    return resp.success(await widget_service.update_widget(db, widget_id, payload), msg="更新成功")


@router.patch("/{widget_id}/toggle", response_model=ResponseModel, summary="启用 / 停用部件")
async def toggle_widget(
    widget_id: int,
    payload: WidgetToggleRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    data = await widget_service.toggle_widget(db, widget_id, payload.is_active)
    return resp.success(data, msg="已启用" if payload.is_active else "已停用")


@router.delete("/{widget_id}", response_model=ResponseModel, summary="删除部件")
async def delete_widget(
    widget_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    await widget_service.delete_widget(db, widget_id)
    return resp.success(None, msg="已删除")
