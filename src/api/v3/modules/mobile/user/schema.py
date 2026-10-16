"""mobile/user 的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class MobilePublicProfileStats(SchemaBase):
    """公开主页的计数（私密资料时全部为 0，不泄露真实值）"""

    articles: int = 0
    followers: int = 0
    following: int = 0


class MobilePublicProfile(SchemaBase):
    """用户公开主页（``GET /mobile/user/public/{username}``）

    字段是**白名单**：绝不包含 email / password / totp_secret / backup_codes /
    last_login_ip / register_ip / is_superuser / is_staff 等任何敏感或权限字段。

    当 ``profile_private`` 为真时只保留 ``id`` / ``username`` / ``profile_picture``，
    其余字段为 null / 0 / false（``bio`` 与 ``stats`` 不泄露真实内容）。
    """

    id: int
    username: Optional[str] = None
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    vip_level: int = 0
    date_joined: Optional[datetime] = None
    is_private: bool = False
    is_following: bool = False
    is_mutual: bool = False
    is_certified: bool = False
    stats: MobilePublicProfileStats = Field(default_factory=MobilePublicProfileStats)


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
