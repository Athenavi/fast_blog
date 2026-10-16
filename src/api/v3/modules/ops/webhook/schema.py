"""webhook 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class WebhookOut(SchemaBase):
    id: int
    name: Optional[str] = None
    url: Optional[str] = None
    events: List[str] = Field(default_factory=list)
    is_active: bool = True
    has_secret: bool = Field(default=False, description="是否配置了签名密钥（不回显密钥本身）")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WebhookCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2048, description="接收回调的地址")
    events: List[str] = Field(default_factory=list, description="订阅的事件名；空表示全部")
    secret: Optional[str] = Field(default=None, max_length=255, description="签名密钥")
    is_active: bool = True


class WebhookUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    events: Optional[List[str]] = None
    secret: Optional[str] = Field(default=None, max_length=255, description="留空表示不修改")
    is_active: Optional[bool] = None


class WebhookEventOut(SchemaBase):
    event: str


class WebhookTestResult(SchemaBase):
    triggered: bool = True
    event: str
    webhook_id: int
    detail: Optional[Any] = None
