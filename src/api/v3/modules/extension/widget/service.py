"""widget 模块业务逻辑

变更操作直接走 ``widget_instances`` 表（v2 的 ``widget_service`` 内存方法有漏 await 缺陷，
不使用）；类型/区域清单复用 ``widget_service`` 的只读方法。
"""

from typing import List, Optional, Sequence, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.widget.widget_instance import WidgetInstance
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.extension.widget.crud import widget_crud
from src.api.v3.modules.extension.widget.schema import (
    WidgetCreate,
    WidgetUpdate,
    dump_json_field,
    parse_json_field,
)

logger = get_logger("widget")


def to_out(widget: WidgetInstance) -> dict:
    return {
        "id": widget.id,
        "widget_type": widget.widget_type,
        "area": widget.area,
        "title": widget.title,
        "config": parse_json_field(widget.config),
        "order_index": widget.order_index or 0,
        "is_active": bool(widget.is_active),
        "conditions": parse_json_field(widget.conditions),
        "created_at": widget.created_at,
        "updated_at": widget.updated_at,
    }


class WidgetService:
    """小部件管理"""

    async def list_widgets(
        self,
        db: AsyncSession,
        *,
        area: Optional[str] = None,
        widget_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[dict]:
        widgets, _total = await widget_crud.list(
            db,
            page=1,
            page_size=0,
            filters={"area": area, "widget_type": widget_type, "is_active": is_active},
            order_by="order_index",
            order="asc",
        )
        return [to_out(widget) for widget in widgets]

    async def get_widget(self, db: AsyncSession, widget_id: int) -> dict:
        widget = await widget_crud.get(db, widget_id)
        if widget is None:
            raise NotFoundError("小部件不存在")
        return to_out(widget)

    async def create_widget(self, db: AsyncSession, payload: WidgetCreate) -> dict:
        widget = await widget_crud.create(
            db,
            {
                "widget_type": payload.widget_type,
                "area": payload.area,
                "title": payload.title,
                "config": dump_json_field(payload.config),
                "order_index": payload.order_index,
                "is_active": payload.is_active,
                "conditions": dump_json_field(payload.conditions),
            },
        )
        return to_out(widget)

    async def update_widget(
        self, db: AsyncSession, widget_id: int, payload: WidgetUpdate
    ) -> dict:
        widget = await widget_crud.get(db, widget_id)
        if widget is None:
            raise NotFoundError("小部件不存在")

        data = payload.model_dump(exclude_unset=True)
        for key in ("config", "conditions"):
            if key in data:
                data[key] = dump_json_field(data[key])
        widget = await widget_crud.update(db, widget, data)
        return to_out(widget)

    async def toggle_widget(self, db: AsyncSession, widget_id: int, is_active: bool) -> dict:
        widget = await widget_crud.get(db, widget_id)
        if widget is None:
            raise NotFoundError("小部件不存在")
        widget = await widget_crud.update(db, widget, {"is_active": is_active})
        return to_out(widget)

    async def delete_widget(self, db: AsyncSession, widget_id: int) -> None:
        widget = await widget_crud.get(db, widget_id)
        if widget is None:
            raise NotFoundError("小部件不存在")
        await widget_crud.remove(db, widget)

    async def reorder(self, db: AsyncSession, items: Sequence[Tuple[int, int]]) -> int:
        if not items:
            raise BadRequestError("items 不能为空")
        count = 0
        for widget_id, order_index in items:
            widget = await widget_crud.get(db, widget_id)
            if widget is None:
                continue
            await widget_crud.update(db, widget, {"order_index": order_index})
            count += 1
        return count

    # ------------------------------------------------------------------ 只读元数据
    async def widget_types(self) -> List[dict]:
        try:
            from shared.services.widgets.widget_manager import widget_service as legacy_widget_service

            return list(legacy_widget_service.get_widget_types() or [])
        except Exception:  # noqa: BLE001 - 元数据缺失不应让接口 500
            logger.exception("读取 widget 类型失败")
            return []

    async def widget_areas(self) -> List[dict]:
        try:
            from shared.services.widgets.widget_manager import widget_service as legacy_widget_service

            return list(legacy_widget_service.get_widget_areas() or [])
        except Exception:  # noqa: BLE001
            logger.exception("读取 widget 区域失败")
            return []

    async def public_by_area(self, db: AsyncSession, area: str) -> List[dict]:
        """前台公开：仅启用的部件，按 order_index 升序"""
        widgets = await self.list_widgets(db, area=area, is_active=True)
        for widget in widgets:
            widget.pop("created_at", None)
            widget.pop("updated_at", None)
        return widgets


widget_service = WidgetService()
