"""article 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: status 语义（与 articles.status 一致）
STATUS_DELETED = -1
STATUS_DRAFT = 0
STATUS_PUBLISHED = 1


class ArticleOut(SchemaBase):
    """列表用：不含正文"""

    id: int
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    cover_image: Optional[str] = None
    category_id: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    views: int = 0
    likes: int = 0
    user_id: Optional[int] = None
    status: Optional[int] = None
    hidden: bool = False
    is_featured: bool = False
    is_sticky: bool = False
    is_vip_only: bool = False
    required_vip_level: int = 0
    post_type: Optional[str] = None
    sort_order: int = 0
    scheduled_publish_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ArticleDetailOut(ArticleOut):
    """详情：带正文与 SEO"""

    content: Optional[str] = Field(default=None, description="正文（默认语言）")
    language_code: Optional[str] = None
    seo: Optional[Dict[str, Any]] = None


class ArticleCreate(SchemaBase):
    title: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    excerpt: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None, description="正文；写入 article_content")
    cover_image: Optional[str] = Field(default=None, max_length=255)
    category_id: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    status: int = Field(default=STATUS_DRAFT, description="-1 删除 / 0 草稿 / 1 已发布")
    hidden: bool = False
    is_featured: bool = False
    is_sticky: bool = False
    is_vip_only: bool = False
    required_vip_level: int = 0
    post_type: str = "article"
    sort_order: int = 0
    scheduled_publish_at: Optional[datetime] = None
    sticky_until: Optional[datetime] = None
    language_code: str = Field(default="zh-CN", description="正文语言")


class ArticleUpdate(SchemaBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    excerpt: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None, description="传入时更新对应语言的正文")
    cover_image: Optional[str] = Field(default=None, max_length=255)
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    status: Optional[int] = None
    hidden: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_sticky: Optional[bool] = None
    is_vip_only: Optional[bool] = None
    required_vip_level: Optional[int] = None
    post_type: Optional[str] = None
    sort_order: Optional[int] = None
    scheduled_publish_at: Optional[datetime] = None
    sticky_until: Optional[datetime] = None
    language_code: Optional[str] = None


class ArticlePublishRequest(SchemaBase):
    publish: bool = Field(default=True, description="true=发布，false=转草稿")


class ArticleBatchDeleteRequest(SchemaBase):
    ids: List[int] = Field(min_length=1, description="待删除文章 id 列表")


class ArticleBatchPublishRequest(SchemaBase):
    ids: List[int] = Field(min_length=1, description="文章 id 列表")
    publish: bool = Field(default=True, description="True 发布 / False 撤回")


class ArticlePublicQuery(SchemaBase):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    category_id: Optional[int] = None
    tag: Optional[str] = None
    keyword: Optional[str] = None
    post_type: Optional[str] = None


class ArticlePreviewTokenCreate(SchemaBase):
    """生成草稿预览令牌（``password`` 是可选的分享口令，只存 Argon2 哈希）"""

    expires_hours: int = Field(
        default=24, ge=1, le=720, description="有效期（小时），上限 30 天"
    )
    password: Optional[str] = Field(
        default=None, min_length=4, max_length=64, description="可选访问口令（≥4 字符）"
    )
    max_views: Optional[int] = Field(
        default=None, ge=1, le=10000, description="可选最大访问次数，为空表示不限"
    )
