"""ai.config 模块的请求 / 响应模型（api_key 只写不读）"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class AIConfigCreate(SchemaBase):
    user_id: int = Field(description="归属用户 ID")
    name: str = Field(min_length=1, max_length=100)
    api_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, description="API Key 明文（入参），落库前加密")
    model: str = Field(min_length=1, max_length=100)
    provider: str = Field(default="openai", max_length=50)
    is_active: bool = False
    sort_order: int = Field(default=0, ge=0)


class AIConfigUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    api_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(default=None, description="留空保持原值")
    model: Optional[str] = Field(default=None, min_length=1, max_length=100)
    provider: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


class AIConfigOut(SchemaBase):
    id: int
    user_id: int
    name: Optional[str] = None
    api_url: Optional[str] = None
    has_api_key: bool = False
    model: Optional[str] = None
    provider: Optional[str] = None
    is_active: bool = False
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
