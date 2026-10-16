"""seo 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class SEOAnalyzeRequest(SchemaBase):
    """对任意内容做 SEO 分析（不落库）"""

    title: str = ""
    description: str = ""
    content: str = ""
    keywords: List[str] = Field(default_factory=list)
    internal_links: int = 0


class SEOAnalyzeResult(SchemaBase):
    overall_score: float = 0.0
    grade: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    suggestions: List[str] = Field(default_factory=list)
    analyzed_at: Optional[str] = None


class ArticleSEOItem(SchemaBase):
    article_id: int
    title: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[int] = None
    score: float = 0.0
    grade: Optional[str] = None
    suggestion_count: int = 0
    top_suggestions: List[str] = Field(default_factory=list)


class ArticleSEOAnalyzeOut(ArticleSEOItem):
    metrics: Dict[str, Any] = Field(default_factory=dict)
    suggestions: List[str] = Field(default_factory=list)


class BulkCheckRequest(SchemaBase):
    ids: List[int] = Field(default_factory=list, description="留空=检查全部已发布文章")
    limit: int = Field(default=50, ge=1, le=500)
    only_published: bool = True


class BulkCheckResult(SchemaBase):
    checked: int = 0
    average_score: float = 0.0
    grade_distribution: Dict[str, int] = Field(default_factory=dict)
    items: List[ArticleSEOItem] = Field(default_factory=list)


class KeywordItem(SchemaBase):
    keyword: str
    count: int = 0
    article_count: int = 0


class OrphanArticle(SchemaBase):
    article_id: int
    title: Optional[str] = None
    slug: Optional[str] = None
    inbound_links: int = 0


class KeywordListResult(SchemaBase):
    keywords: List[KeywordItem] = Field(default_factory=list)
    total: int = 0


class OrphanListResult(SchemaBase):
    items: List[OrphanArticle] = Field(default_factory=list)
    total: int = 0
    total_articles: int = 0


class LinkDistributionOut(SchemaBase):
    total_articles: int = 0
    total_links: int = 0
    average_links: float = 0.0
    distribution: Dict[str, Any] = Field(default_factory=dict)


class SEOReportOut(SchemaBase):
    generated_at: datetime
    total_articles: int = 0
    analyzed_articles: int = 0
    average_score: float = 0.0
    grade_distribution: Dict[str, int] = Field(default_factory=dict)
    common_suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    orphan_count: int = 0
    top_keywords: List[KeywordItem] = Field(default_factory=list)
