"""site 模块的请求 / 响应模型"""

import json
from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase


def _loads_json(value):  # noqa: ANN001, ANN202 - pydantic validator
    """JSON 字符串列容错解析：非法/空值原样返回 None（列里存的是 JSON 字符串）"""
    if value is None or isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


class SiteCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, description="站点标识，创建后锁定")
    domain: str = Field(min_length=1, max_length=255, description="主域名")
    additional_domains: Optional[list[str]] = Field(default=None, description="附加域名列表")
    description: Optional[str] = None
    logo_url: Optional[str] = Field(default=None, max_length=500)
    favicon_url: Optional[str] = Field(default=None, max_length=500)
    theme: str = Field(default="default", max_length=100)
    language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)
    settings: Optional[dict] = Field(default=None, description="站点设置（JSON）")
    is_active: bool = True
    is_default: bool = False


class SiteUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    domain: Optional[str] = Field(default=None, min_length=1, max_length=255)
    additional_domains: Optional[list[str]] = None
    description: Optional[str] = None
    logo_url: Optional[str] = Field(default=None, max_length=500)
    favicon_url: Optional[str] = Field(default=None, max_length=500)
    theme: Optional[str] = Field(default=None, max_length=100)
    language: Optional[str] = Field(default=None, max_length=10)
    timezone: Optional[str] = Field(default=None, max_length=50)
    settings: Optional[dict] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class SiteOut(SchemaBase):
    id: int
    name: Optional[str] = None
    slug: Optional[str] = None
    domain: Optional[str] = None
    additional_domains: Optional[list[str]] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    settings: Optional[dict] = None
    is_active: bool = True
    is_default: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # JSON 字符串列：from_attributes 直灌 str 会 ValidationError，先解析
    @field_validator("additional_domains", "settings", mode="before")
    @classmethod
    def _parse_json_columns(cls, value):  # noqa: ANN001, ANN202
        return _loads_json(value)
