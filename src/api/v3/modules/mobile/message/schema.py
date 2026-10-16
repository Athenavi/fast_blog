"""mobile/message 的请求模型（前台站内信）

安全设计：**只暴露发送端应当控制的字段**。
`is_read` / `read_at` / 双向软删标志（`is_deleted_by_sender` / `is_deleted_by_recipient`）/
`created_at` / `updated_at` 这些状态字段一律不出现在请求模型里，由服务端强制设定。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class MobileMessageCreate(SchemaBase):
    """发送私信。

    `recipient_id` 为自己时由 service 层拒绝（400）；收件人不存在返回 404；
    `parent_message` 给出时必须指向真实存在的消息（回复）。
    """

    recipient_id: int = Field(description="收件人用户 ID")
    content: str = Field(min_length=1, max_length=5000, description="消息内容")
    message_type: str = Field(
        default="text", max_length=50, description="消息类型（text/image/file 等）"
    )
    attachment_url: Optional[str] = Field(
        default=None, max_length=500, description="附件 URL（图片/文件）"
    )
    parent_message: Optional[int] = Field(default=None, description="父消息 ID（回复某条消息）")
