"""chat.group 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class ChatGroupCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=255)
    avatar: Optional[str] = Field(default=None, max_length=255)
    creator: int = Field(description="创建者用户 ID")
    is_active: bool = True


class ChatGroupUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=255)
    avatar: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class ChatGroupOut(SchemaBase):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    creator: Optional[int] = None
    member_count: int = 0
    last_message_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GroupMemberAdd(SchemaBase):
    user_id: int = Field(description="被加入的用户 ID")
    role: str = Field(default="member", description="owner/admin/member")


class GroupMemberUpdate(SchemaBase):
    role: Optional[str] = Field(default=None, description="owner/admin/member")
    is_muted: Optional[bool] = None


class GroupMemberOut(SchemaBase):
    id: int
    group: int
    user: int
    role: Optional[str] = None
    joined_at: Optional[datetime] = None
    last_read_at: Optional[datetime] = None
    is_muted: bool = False
