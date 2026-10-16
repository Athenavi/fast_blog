"""mobile/media 的查询模型

前台用户端的媒体库只暴露「自己的」数据，因此这里只需要分页与筛选参数，
不需要后台那套 `is_public` / `user_id` 的越权维度。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class MobileMediaQuery(SchemaBase):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=24, ge=1, le=100)
    folder_id: Optional[int] = Field(default=None, description="按文件夹筛选")
    mime_type: Optional[str] = Field(default=None, description="前缀匹配，如 image/")
    keyword: Optional[str] = Field(default=None, description="文件名关键词")


class MobileMediaUpdate(SchemaBase):
    """前台可自助修改的字段白名单（与后台一致，但不含 `is_public` 等管理项）"""

    description: Optional[str] = Field(default=None, max_length=255)
    alt_text: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[list[str]] = None
    folder_id: Optional[int] = None


class MobileFolderCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=255)
    parent_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=255)
    sort_order: int = 0


class MobileMediaStats(SchemaBase):
    total: int = 0
    total_size: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
