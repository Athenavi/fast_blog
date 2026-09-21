"""chat.message 模块的请求 / 响应模型。

安全设计：请求模型只暴露发送端应当控制的字段；``user`` / ``is_deleted`` /
``created_at`` 等状态字段由服务端强制设定，不出现在 ``ChatMessageCreate`` 里。
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class ChatMessageCreate(SchemaBase):
    """发送群聊消息。

    发送者固定为当前登录用户；``group_id`` 必须是该用户所在的群（否则 403）。
    """

    group_id: int = Field(description="群聊 ID")
    content: str = Field(min_length=1, max_length=2000, description="消息内容")
    message_type: str = Field(
        default="text", max_length=50, description="消息类型（text/image/file/system）"
    )
    attachment_url: Optional[str] = Field(
        default=None, max_length=500, description="附件 URL（图片/文件）"
    )
    parent_message: Optional[int] = Field(default=None, description="引用的消息 ID（回复）")


class ChatMessageOut(SchemaBase):
    """对外输出的一条群聊消息。

    响应列表项与 WebSocket 广播负载共用**同一字段集**（见 ``service.serialize_message``）。
    撤回消息 ``is_deleted=True`` 且 ``content`` 为空串。
    """

    id: int
    group_id: int
    user_id: int
    username: Optional[str] = None
    content: str
    message_type: Optional[str] = None
    attachment_url: Optional[str] = None
    parent_message: Optional[int] = None
    is_deleted: bool = False
    created_at: Optional[datetime] = None


class MyChatGroupOut(SchemaBase):
    """我加入的群聊（前台聊天页左栏）

    只列**本人加入**的群，因此不需要 `module_chat:group:view` 管理权限。
    """

    id: int
    name: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    member_count: int = 0
    last_message_at: Optional[datetime] = None
    role: Optional[str] = None
