"""role 模块的请求 / 响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class RoleOut(SchemaBase):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_system: bool = False
    is_active: bool = True
    parent_id: Optional[int] = None
    #: 数据范围（1 仅本人 / 2 本组及以下 / 3 全部 / 5 自定义组）；=5 时由权限组决定可见范围
    data_scope: Optional[int] = None
    created_at: Optional[datetime] = None
    permission_count: int = 0
    user_count: int = 0


class RoleCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=50, description="唯一标识，如 editor")
    description: Optional[str] = None
    parent_id: Optional[int] = Field(default=None, description="父角色 id（权限继承）")
    permission_codes: List[str] = Field(default_factory=list, description="权限码列表")


class RoleUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class RolePermissionsRequest(SchemaBase):
    permission_codes: List[str] = Field(default_factory=list, description="全量覆盖角色的权限码")


class RoleBrief(SchemaBase):
    id: int
    name: str
    slug: str
