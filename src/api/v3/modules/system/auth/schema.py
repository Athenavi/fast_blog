"""auth 模块的请求 / 响应模型"""

from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class LoginRequest(SchemaBase):
    """登录请求（``username`` 与 ``email`` 二选一，兼容 v2 的调用方式）"""

    username: Optional[str] = Field(default=None, description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱")
    password: str = Field(description="密码")
    remember_me: bool = Field(default=False, description="是否签发 refresh token")


class RefreshRequest(SchemaBase):
    refresh_token: Optional[str] = Field(default=None, description="留空时从 cookie 读取")


class TokenPayload(SchemaBase):
    """登录结果"""

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = Field(default=None, description="access token 有效期（秒）")
    email_verified: bool = False
    requires_2fa: bool = Field(default=False, description="是否需要二次验证")
    temp_token: Optional[str] = Field(default=None, description="2FA 临时令牌")
    message: Optional[str] = None


class CurrentUserOut(SchemaBase):
    """当前登录用户信息（含角色与权限码，供前端生成菜单与按钮权限）"""

    id: int
    username: str
    email: Optional[str] = None
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    vip_level: int = 0
    locale: Optional[str] = None
    profile_picture: Optional[str] = None
    roles: List[str] = Field(default_factory=list, description="角色 slug 列表")
    permissions: List[str] = Field(default_factory=list, description="权限码（resource:action）")


class LoginStatusOut(SchemaBase):
    logged_in: bool
    user_id: Optional[int] = None


class Verify2FARequest(SchemaBase):
    temp_token: str = Field(description="登录时返回的临时令牌")
    code: str = Field(description="TOTP 验证码")
