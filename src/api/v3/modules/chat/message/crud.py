"""chat.message 模块的数据访问层（唯一 DB 访问点）。

表 ``chat_messages``（群聊消息，批次 17 新建）。

注意：本模块的**消息列表**不能走 ``CRUDBase.list`` —— 后者会按
``soft_delete_field`` 过滤掉 ``is_deleted=True`` 的撤回消息，而撤回消息仍需
返回给前端（显示「已撤回」）。因此列表查询在 ``service.py`` 里用原生 ``select``
手写；这里的 ``soft_delete_field`` 只影响 ``CRUDBase.get/remove`` 的软删语义。
"""

from shared.models.chat import ChatMessage
from src.api.v3.core.base_crud import CRUDBase


class ChatMessageCRUD(CRUDBase[ChatMessage, dict, dict]):
    model = ChatMessage
    keyword_fields = ("content",)
    default_order_by = "id"
    soft_delete_field = "is_deleted"


chat_message_crud = ChatMessageCRUD()
