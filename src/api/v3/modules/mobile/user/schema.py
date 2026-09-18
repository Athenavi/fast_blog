"""mobile/user 的请求 / 响应模型"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class MobileProfileUpdate(SchemaBase):
    """移动端可自助修改的字段白名单（用户名 / 邮箱 / 权限不可自助修改）"""

    profile_picture: Optional[str] = Field(default=None, max_length=255)
    bio: Optional[str] = Field(default=None, max_length=500)
    locale: Optional[str] = Field(default=None, max_length=20)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class MobileUserStats(SchemaBase):
    articles: int = 0
    comments: int = 0
    likes_received: int = 0
