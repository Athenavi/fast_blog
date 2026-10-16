"""category 模块的请求 / 响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class CategoryOut(SchemaBase):
    id: int
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 0
    icon: Optional[str] = None
    color: Optional[str] = None
    is_visible: bool = True
    articles_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: List["CategoryOut"] = Field(default_factory=list)


CategoryOut.model_rebuild()


class CategoryCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=255)
    parent_id: Optional[int] = None
    sort_order: int = 0
    icon: Optional[str] = Field(default=None, max_length=255)
    color: Optional[str] = Field(default=None, max_length=255)
    is_visible: bool = True


class CategoryUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=255)
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_visible: Optional[bool] = None


class CategoryMergeRequest(SchemaBase):
    """合并：把当前分类并入 `target_id`（其子分类与文章会一并迁移）"""

    target_id: int = Field(description="目标分类 id")
