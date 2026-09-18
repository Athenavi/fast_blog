"""group 模块的请求 / 响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class PermissionGroupOut(SchemaBase):
    id: int
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 0
    owner_id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    #: 统计字段（列表/详情时填充）
    member_count: int = 0
    children: List["PermissionGroupOut"] = Field(default_factory=list)


PermissionGroupOut.model_rebuild()


class PermissionGroupCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100, description="组标识（唯一）")
    description: Optional[str] = Field(default=None, max_length=255)
    parent_id: Optional[int] = None
    sort_order: int = 0
    owner_id: Optional[int] = Field(default=None, description="组长用户 id")
    is_active: bool = True


class PermissionGroupUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    owner_id: Optional[int] = None
    is_active: Optional[bool] = None


class GroupMemberOut(SchemaBase):
    id: int
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True


class GroupMemberAssign(SchemaBase):
    user_ids: List[int] = Field(default_factory=list, description="全量覆盖该组成员")


class GroupRoleOut(SchemaBase):
    id: int
    name: Optional[str] = None
    slug: Optional[str] = None
    data_scope: Optional[int] = None


class GroupRoleAssign(SchemaBase):
    role_ids: List[int] = Field(
        default_factory=list, description="绑定到该组的角色（配合 roles.data_scope=5 使用）"
    )
