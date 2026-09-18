"""webhook 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.webhook.webhook import Webhook
from src.api.v3.core.base_crud import CRUDBase


class WebhookCRUD(CRUDBase[Webhook, dict, dict]):
    model = Webhook
    keyword_fields = ("name", "url")
    default_order_by = "id"


webhook_crud = WebhookCRUD()
