"""notification 模块的数据访问层（唯一 DB 访问点）"""

from shared.models import Notification
from src.api.v3.core.base_crud import CRUDBase


class NotificationCRUD(CRUDBase[Notification, dict, dict]):
    model = Notification
    keyword_fields = ("title", "message", "type")
    default_order_by = "id"


notification_crud = NotificationCRUD()
