"""email 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class EmailConfigCreate(SchemaBase):
    provider: str = Field(default="smtp", max_length=30, description="smtp/sendgrid/mailgun…")
    api_key: Optional[str] = Field(default=None, max_length=255)
    smtp_host: Optional[str] = Field(default=None, max_length=200)
    smtp_port: Optional[int] = Field(default=None, ge=1, le=65535)
    smtp_username: Optional[str] = Field(default=None, max_length=200)
    smtp_password: Optional[str] = Field(default=None, max_length=255)
    from_email: str = Field(max_length=200)
    from_name: Optional[str] = Field(default=None, max_length=200)
    enable_batch_sending: bool = False
    batch_size: int = Field(default=50, ge=1)
    daily_limit: int = Field(default=1000, ge=1)
    is_active: bool = True


class EmailConfigUpdate(SchemaBase):
    provider: Optional[str] = Field(default=None, max_length=30)
    api_key: Optional[str] = Field(default=None, max_length=255)
    smtp_host: Optional[str] = Field(default=None, max_length=200)
    smtp_port: Optional[int] = Field(default=None, ge=1, le=65535)
    smtp_username: Optional[str] = Field(default=None, max_length=200)
    smtp_password: Optional[str] = Field(default=None, max_length=255)
    from_email: Optional[str] = Field(default=None, max_length=200)
    from_name: Optional[str] = Field(default=None, max_length=200)
    enable_batch_sending: Optional[bool] = None
    batch_size: Optional[int] = Field(default=None, ge=1)
    daily_limit: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class EmailConfigOut(SchemaBase):
    """凭据脱敏：api_key / smtp_password 只返回是否已设置的布尔位"""

    id: int
    provider: Optional[str] = None
    has_api_key: bool = False
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    has_smtp_password: bool = False
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    enable_batch_sending: bool = False
    batch_size: int = 50
    daily_limit: int = 1000
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EmailSubscriptionOut(SchemaBase):
    id: int
    user_id: Optional[int] = None
    subscribed: bool = False
    created_at: Optional[datetime] = None
