"""custom_post_type 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class CustomPostTypeCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern="^[a-z0-9_-]+$")
    description: Optional[str] = Field(default=None, max_length=255)
    supports: Optional[str] = Field(default=None, max_length=255,
                                    description="支持的功能（逗号分隔：title,editor,thumbnail…）")
    has_archive: bool = False
    menu_icon: Optional[str] = Field(default=None, max_length=100)
    menu_position: int = Field(default=0, ge=0)
    is_active: bool = True


class CustomPostTypeUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    supports: Optional[str] = Field(default=None, max_length=255)
    has_archive: Optional[bool] = None
    menu_icon: Optional[str] = Field(default=None, max_length=100)
    menu_position: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class CustomPostTypeOut(SchemaBase):
    id: int
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    supports: Optional[str] = None
    has_archive: bool = False
    menu_icon: Optional[str] = None
    menu_position: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
