"""dashboard 模块的响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class OverviewOut(SchemaBase):
    """统计概览"""

    total_articles: int = 0
    published_articles: int = 0
    draft_articles: int = 0
    total_users: int = 0
    active_users: int = 0
    total_comments: int = 0
    pending_comments: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_categories: int = 0
    total_media: int = 0


class TrendPoint(SchemaBase):
    day: str
    articles: int = 0
    comments: int = 0
    users: int = 0


class TrendOut(SchemaBase):
    days: int
    points: List[TrendPoint] = Field(default_factory=list)


class RecentArticleOut(SchemaBase):
    id: int
    title: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[int] = None
    views: int = 0
    created_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


class RecentCommentOut(SchemaBase):
    id: int
    article_id: Optional[int] = None
    content: Optional[str] = None
    author_name: Optional[str] = None
    is_approved: bool = False
    created_at: Optional[datetime] = None


class TopArticleOut(SchemaBase):
    id: int
    title: Optional[str] = None
    views: int = 0
    likes: int = 0
