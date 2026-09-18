"""media 模块的请求 / 响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class MediaOut(SchemaBase):
    """媒体条目（不含 ``file_path``，避免暴露服务器磁盘结构）"""

    id: int
    user_id: Optional[int] = None
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    file_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    alt_text: Optional[str] = None
    is_public: bool = True
    download_count: int = 0
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="逗号分隔字段解析后的列表")
    folder_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MediaUpdate(SchemaBase):
    description: Optional[str] = Field(default=None, max_length=255)
    alt_text: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[List[str]] = None
    folder_id: Optional[int] = None
    is_public: Optional[bool] = None


class MediaBatchDeleteRequest(SchemaBase):
    ids: List[int] = Field(min_length=1)


class MediaFolderOut(SchemaBase):
    id: int
    name: str
    parent_id: Optional[int] = None
    user_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: int = 0
    is_public: bool = True
    media_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: List["MediaFolderOut"] = Field(default_factory=list)


MediaFolderOut.model_rebuild()


class MediaFolderCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=255)
    parent_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=255)
    sort_order: int = 0
    is_public: bool = True


class MediaFolderUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    parent_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=255)
    sort_order: Optional[int] = None
    is_public: Optional[bool] = None
