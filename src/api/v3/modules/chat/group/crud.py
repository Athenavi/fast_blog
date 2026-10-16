"""chat.group 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.chat import ChatGroup, ChatGroupMember
from src.api.v3.core.base_crud import CRUDBase


class ChatGroupCRUD(CRUDBase[ChatGroup, dict, dict]):
    model = ChatGroup
    keyword_fields = ("name", "description")
    default_order_by = "id"


class ChatGroupMemberCRUD(CRUDBase[ChatGroupMember, dict, dict]):
    model = ChatGroupMember
    keyword_fields = ("role",)
    default_order_by = "id"


chat_group_crud = ChatGroupCRUD()
chat_group_member_crud = ChatGroupMemberCRUD()
