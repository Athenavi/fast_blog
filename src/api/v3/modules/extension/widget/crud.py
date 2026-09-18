"""widget 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.widget.widget_instance import WidgetInstance
from src.api.v3.core.base_crud import CRUDBase


class WidgetCRUD(CRUDBase[WidgetInstance, dict, dict]):
    model = WidgetInstance
    keyword_fields = ("title", "widget_type", "area")
    default_order_by = "order_index"


widget_crud = WidgetCRUD()
