"""block_pattern 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class BlockPatternCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=50)
    blocks: Optional[str] = None
    keywords: Optional[str] = Field(default=None, max_length=255, description="逗号分隔关键词")
    thumbnail: Optional[str] = Field(default=None, max_length=500)
    is_public: bool = False


class BlockPatternUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=50)
    blocks: Optional[str] = None
    keywords: Optional[str] = Field(default=None, max_length=255)
    thumbnail: Optional[str] = Field(default=None, max_length=500)
    is_public: Optional[bool] = None


class BlockPatternOut(SchemaBase):
    id: int
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    blocks: Optional[str] = None
    keywords: Optional[str] = None
    thumbnail: Optional[str] = None
    is_public: bool = False
    viewport_width: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
