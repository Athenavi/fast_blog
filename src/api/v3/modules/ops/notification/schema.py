"""notification 模块的响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class NotificationOut(SchemaBase):
    id: int
    recipient: Optional[int] = Field(default=None, description="接收人 id（即当前用户）")
    type: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class UnreadCountOut(SchemaBase):
    unread: int = 0


class AffectedOut(SchemaBase):
    affected: int = 0


class NotificationBatchRequest(SchemaBase):
    """批量操作本人通知：标记已读 / 删除"""

    ids: List[int] = Field(min_length=1, description="通知 id 列表")
