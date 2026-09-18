"""mobile/auth 的请求 / 响应模型"""

from typing import Optional

from pydantic import EmailStr, Field

from src.api.v3.core.base_schema import SchemaBase


class MobileLoginRequest(SchemaBase):
    username: Optional[str] = Field(default=None, description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱")
    password: str = Field(min_length=1)
    remember_me: bool = Field(default=True, description="移动端默认签发 refresh token")


class MobileRegisterRequest(SchemaBase):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class MobileTokenOut(SchemaBase):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    requires_2fa: bool = False
    temp_token: Optional[str] = None
    message: Optional[str] = None
