"""user 模块的请求 / 响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr, Field

from src.api.v3.core.base_schema import SchemaBase


class UserOut(SchemaBase):
    """用户信息（不含密码等敏感字段）"""

    id: int
    username: str
    email: Optional[str] = None
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    vip_level: int = 0
    vip_expires_at: Optional[datetime] = None
    locale: Optional[str] = None
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    date_joined: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class UserCreate(SchemaBase):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    role_ids: List[int] = Field(default_factory=list, description="初始角色 id 列表")


class UserUpdate(SchemaBase):
    """局部更新：未传的字段不修改（``exclude_unset`` 语义）"""

    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    is_active: Optional[bool] = None
    is_staff: Optional[bool] = None
    locale: Optional[str] = None
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    vip_level: Optional[int] = None


class UserStatusUpdate(SchemaBase):
    is_active: bool


class RoleAssignRequest(SchemaBase):
    role_ids: List[int] = Field(default_factory=list, description="目标角色 id 列表（全量覆盖）")


class RoleBrief(SchemaBase):
    id: int
    name: str
    slug: str
