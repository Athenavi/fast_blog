"""
V3 Widget 管理 API

权限要求:
  GET    /widgets             → settings:view
  GET    /widgets/types       → settings:view
  POST   /widgets             → settings:edit
  PUT    /widgets/{id}        → settings:edit
  PATCH  /widgets/{id}/toggle → settings:edit
  DELETE /widgets/{id}        → settings:edit
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.widget.widget_instance import WidgetInstance
from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db
from src.api.v3._permission import Permission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-widgets"])


@router.get("/widgets", summary="Widget 列表")
async def list_widgets(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:view")),
):
    result = await db.execute(
        select(WidgetInstance).order_by(WidgetInstance.order_index, WidgetInstance.id)
    )
    items = result.scalars().all()
    return ApiResponse(success=True, data={"widgets": [_w_dict(w) for w in items]})


@router.get("/widgets/types", summary="Widget 类型列表")
async def list_widget_types(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:view")),
):
    types = ["html", "menu", "recent_posts", "categories", "tags", "search", "text"]
    return ApiResponse(success=True, data={"types": types})


@router.get("/widgets/areas", summary="Widget 区域列表")
async def list_widget_areas(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:view")),
):
    areas = ["sidebar_primary", "sidebar_secondary", "footer_1", "footer_2", "footer_3", "header", "content_top", "content_bottom"]
    return ApiResponse(success=True, data={"areas": [{"id": a, "name": a.replace("_", " ").title()} for a in areas]})


@router.post("/widgets", summary="创建 Widget", status_code=201)
async def create_widget(
    title: str = Body(...),
    widget_type: str = Body(...),
    config: str = Body(""),
    area: str = Body("sidebar"),
    order_index: int = Body(0),
    is_active: bool = Body(True),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:edit")),
):
    now = datetime.now(timezone.utc)
    item = WidgetInstance(
        widget_type=widget_type,
        area=area,
        title=title,
        config=config,
        order_index=order_index,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ApiResponse(success=True, data=_w_dict(item), message="Widget 创建成功")


@router.put("/widgets/{widget_id}", summary="更新 Widget")
async def update_widget(
    widget_id: int,
    title: str = Body(None),
    widget_type: str = Body(None),
    config: str = Body(None),
    area: str = Body(None),
    order_index: int = Body(None),
    is_active: bool = Body(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:edit")),
):
    item = await db.get(WidgetInstance, widget_id)
    if not item:
        return ApiResponse(success=False, error="Widget 不存在")
    if title is not None: item.title = title
    if widget_type is not None: item.widget_type = widget_type
    if config is not None: item.config = config
    if area is not None: item.area = area
    if order_index is not None: item.order_index = order_index
    if is_active is not None: item.is_active = is_active
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse(success=True, message="Widget 已更新")


@router.patch("/widgets/{widget_id}/toggle", summary="切换 Widget 状态")
async def toggle_widget(
    widget_id: int,
    is_active: bool = Body(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:edit")),
):
    item = await db.get(WidgetInstance, widget_id)
    if not item:
        return ApiResponse(success=False, error="Widget 不存在")
    item.is_active = is_active
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse(success=True, message=f"Widget {'已启用' if is_active else '已停用'}")


@router.delete("/widgets/{widget_id}", summary="删除 Widget")
async def delete_widget(
    widget_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:edit")),
):
    item = await db.get(WidgetInstance, widget_id)
    if not item:
        return ApiResponse(success=False, error="Widget 不存在")
    await db.delete(item)
    await db.commit()
    return ApiResponse(success=True, message="Widget 已删除")


def _w_dict(w: WidgetInstance) -> dict:
    return {
        "id": w.id,
        "title": w.title,
        "widget_type": w.widget_type,
        "config": w.config,
        "area": w.area,
        "order_index": w.order_index,
        "is_active": w.is_active,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }
