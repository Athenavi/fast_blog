"""page 模块的请求 / 响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

STATUS_DRAFT = 0
STATUS_PUBLISHED = 1


class PageOut(SchemaBase):
    """列表用：不含正文"""

    id: int
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    template: Optional[str] = None
    status: Optional[int] = None
    author_id: Optional[int] = None
    parent_id: Optional[int] = None
    order_index: int = 0
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PageDetailOut(PageOut):
    content: Optional[str] = None


class PageCreate(SchemaBase):
    title: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = None
    excerpt: Optional[str] = Field(default=None, max_length=255)
    template: Optional[str] = Field(default=None, max_length=255)
    status: int = Field(default=STATUS_DRAFT, description="0 草稿 / 1 已发布")
    parent_id: Optional[int] = None
    order_index: int = 0
    meta_title: Optional[str] = Field(default=None, max_length=255)
    meta_description: Optional[str] = Field(default=None, max_length=255)
    meta_keywords: Optional[str] = Field(default=None, max_length=255)


class PageUpdate(SchemaBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = None
    excerpt: Optional[str] = Field(default=None, max_length=255)
    template: Optional[str] = Field(default=None, max_length=255)
    status: Optional[int] = None
    parent_id: Optional[int] = None
    order_index: Optional[int] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None


class PagePublishRequest(SchemaBase):
    publish: bool = Field(default=True, description="true=发布，false=转草稿")


class PageBatchDeleteRequest(SchemaBase):
    ids: List[int] = Field(min_length=1)
