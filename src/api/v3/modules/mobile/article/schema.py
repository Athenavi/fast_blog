"""mobile/article 的请求模型（用户投稿）

安全设计：**只暴露作者端应当控制的字段**。
`status`、`is_featured`、`is_sticky`、`hidden`、`is_vip_only`、`required_vip_level`、
`sort_order`、`scheduled_publish_at` 这些**管理字段一律不出现在请求模型里**，
由 service 强制置为草稿与默认值——否则前台用户就能自行发布/置顶/加精。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class MobileArticleCreate(SchemaBase):
    title: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    excerpt: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None, description="正文；写入 article_content")
    cover_image: Optional[str] = Field(default=None, max_length=255)
    category_id: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    language_code: str = Field(default="zh-CN")


class MobileArticleUpdate(SchemaBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    excerpt: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None)
    cover_image: Optional[str] = Field(default=None, max_length=255)
    category_id: Optional[int] = None
    tags: Optional[list[str]] = None
    language_code: Optional[str] = None


class MobileArticleQuery(SchemaBase):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[int] = Field(default=None, description="0 草稿 / 1 已发布")
    keyword: Optional[str] = None
