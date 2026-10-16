"""GraphQL 类型定义。

刻意**显式白名单**地把 service 返回的 dict 投影成图类型，而不是直接把 dict 摊开：

  - 避免 service 内部字段（内部路径、审计字段等）无意间暴露给匿名查询；
  - 字段增删由这里显式决定，不会被 service 的演进"顺带"改变对外契约。
"""

from datetime import datetime
from typing import List, Optional

import strawberry


@strawberry.type
class Article:
    """文章（列表与详情共用；仅详情会带 content/language_code/locked）"""

    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    cover_image: Optional[str] = None
    category_id: Optional[int] = None
    tags: List[str] = strawberry.field(default_factory=list)
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
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    #: 详情专属：VIP 受限时正文为空且 locked=True（与 REST 的公开详情同一口径）
    content: Optional[str] = None
    language_code: Optional[str] = None
    locked: Optional[bool] = None

    @strawberry.field(description="所属分类（DataLoader 批量加载，避免 N+1）")
    async def category(self, info: strawberry.Info) -> Optional["Category"]:
        from src.api.v3.graphql.loaders import load_category

        if self.category_id is None:
            return None
        data = await load_category(info.context, self.category_id)
        return to_category(data) if data else None


@strawberry.type
class ArticleConnection:
    items: List[Article]
    total: int
    page: int
    page_size: int


@strawberry.type
class Category:
    id: int
    name: str
    slug: Optional[str] = None
    parent_id: Optional[int] = None


@strawberry.type
class Tag:
    id: int
    name: str
    count: Optional[int] = None


@strawberry.type
class Viewer:
    """当前身份（匿名时为 null）"""

    id: int
    username: str
    email: Optional[str] = None
    is_superuser: bool = False


def to_article(data: dict, *, with_content: bool = False) -> Article:
    """dict → Article。字段缺失给默认值，不因为某个键缺席而整体报错。"""
    return Article(
        id=int(data.get("id") or 0),
        title=str(data.get("title") or ""),
        slug=str(data.get("slug") or ""),
        excerpt=data.get("excerpt"),
        cover_image=data.get("cover_image"),
        category_id=data.get("category_id"),
        tags=list(data.get("tags") or []),
        views=int(data.get("views") or 0),
        likes=int(data.get("likes") or 0),
        user_id=data.get("user_id"),
        status=data.get("status"),
        hidden=bool(data.get("hidden", False)),
        is_featured=bool(data.get("is_featured", False)),
        is_sticky=bool(data.get("is_sticky", False)),
        is_vip_only=bool(data.get("is_vip_only", False)),
        required_vip_level=int(data.get("required_vip_level") or 0),
        post_type=data.get("post_type"),
        published_at=data.get("published_at"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        content=data.get("content") if with_content else None,
        language_code=data.get("language_code") if with_content else None,
        locked=data.get("locked") if with_content else None,
    )


def to_category(data: dict) -> Category:
    return Category(
        id=int(data.get("id") or 0),
        name=str(data.get("name") or ""),
        slug=data.get("slug"),
        parent_id=data.get("parent_id") or data.get("parent"),
    )


def to_tag(data: dict) -> Tag:
    return Tag(
        id=int(data.get("id") or 0),
        name=str(data.get("name") or ""),
        count=data.get("count") or data.get("article_count"),
    )


def to_viewer(user) -> Viewer:
    return Viewer(
        id=int(getattr(user, "id", 0) or 0),
        username=str(getattr(user, "username", "") or ""),
        email=getattr(user, "email", None),
        is_superuser=bool(getattr(user, "is_superuser", False)),
    )
