"""RSS / Atom Feed 生成服务

职责划分（合并自两份历史实现）：
  - 取数：本模块负责查库（文章 + 作者 + 分类 + 正文），一次查询取回，无 N+1
  - 序列化：复用 ``src/utils/feed_generator.py``（RSS 2.0 / Atom 1.0 的唯一生成器）

历史实现里指向 ``/api/v1/feed/*`` 的链接是 v2 时代的死链，这里统一用 v3 权威路径
``RSS_PATH`` / ``ATOM_PATH``（与 ``analytics/seo/feed.py`` 的路由一致）。
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging import default_logger as logger
from shared.models.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.category import Category
from shared.models.user import User
from src.utils.feed_generator import FeedItem, RSSFeedGenerator

#: feed 端点的权威路径（对外可发现的地址）
RSS_PATH = "/api/v3/analytics/seo/feed/rss"
ATOM_PATH = "/api/v3/analytics/seo/feed/atom"

DEFAULT_TITLE = "FastBlog"
DEFAULT_DESCRIPTION = "最新文章订阅"
DEFAULT_LANGUAGE = "zh-CN"


def _article_link(base_url: str, article: Article) -> str:
    """文章对外 URL（与 sitemap 的规则保持一致）"""
    if article.slug:
        return f"{base_url}/articles/{article.slug}"
    return f"{base_url}/articles/id/{article.id}"


async def _load_items(
    db: AsyncSession,
    *,
    base_url: str,
    limit: int,
    category_id: Optional[int],
) -> List[FeedItem]:
    """取回 feed 条目（作者 / 分类 / 正文各一次批量查询）"""
    stmt = (
        select(Article)
        .where(Article.status == 1)
        .order_by(Article.created_at.desc())
        .limit(limit)
    )
    if category_id:
        stmt = stmt.where(Article.category == category_id)

    articles = (await db.execute(stmt)).scalars().all()
    if not articles:
        return []

    article_ids = [article.id for article in articles]
    author_ids = {int(article.user) for article in articles if article.user}
    category_ids = {int(article.category) for article in articles if article.category}

    authors: Dict[int, str] = {}
    if author_ids:
        rows = (
            await db.execute(
                select(User.id, User.username, User.email).where(User.id.in_(author_ids))
            )
        ).all()
        authors = {int(uid): (email or username or "") for uid, username, email in rows}

    categories: Dict[int, str] = {}
    if category_ids:
        rows = (
            await db.execute(
                select(Category.id, Category.name).where(Category.id.in_(category_ids))
            )
        ).all()
        categories = {int(cid): (name or "") for cid, name in rows}

    contents: Dict[int, str] = {}
    rows = (
        await db.execute(
            select(ArticleContent.article, ArticleContent.content)
            .where(ArticleContent.article.in_(article_ids))
            .order_by(ArticleContent.id.asc())
        )
    ).all()
    for aid, content in rows:
        # 同一篇文章可能有多个语言版本，取 id 最小的（默认语言）作为正文
        contents.setdefault(int(aid), content or "")

    now = datetime.now(timezone.utc)
    items: List[FeedItem] = []
    for article in articles:
        tags: Sequence[Any] = article.tags_list if isinstance(article.tags_list, list) else []
        item_categories = [str(tag) for tag in tags if tag]
        category_name = categories.get(int(article.category)) if article.category else None
        if category_name:
            item_categories.append(category_name)

        items.append(
            FeedItem(
                title=article.title or "",
                link=_article_link(base_url, article),
                description=article.excerpt or "",
                pub_date=article.created_at or now,
                author=authors.get(int(article.user)) if article.user else None,
                categories=item_categories,
                content=contents.get(int(article.id)) or None,
                image=article.cover_image or None,
            )
        )
    return items


def _build_generator(
    *,
    base_url: str,
    feed_path: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> RSSFeedGenerator:
    return RSSFeedGenerator(
        title=title or DEFAULT_TITLE,
        link=base_url,
        description=description or DEFAULT_DESCRIPTION,
        language=DEFAULT_LANGUAGE,
        feed_url=f"{base_url}{feed_path}",
    )


async def generate_rss_feed(
    db: AsyncSession,
    base_url: str = "http://localhost:8000",
    limit: int = 20,
    category_id: Optional[int] = None,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """生成 RSS 2.0 订阅内容（失败时返回空串，由调用方决定响应）"""
    try:
        generator = _build_generator(
            base_url=base_url, feed_path=RSS_PATH, title=title, description=description
        )
        for item in await _load_items(
            db, base_url=base_url, limit=limit, category_id=category_id
        ):
            generator.add_item(item)
        return generator.generate_rss()
    except Exception as exc:  # noqa: BLE001 - feed 失败不应影响站点其他功能
        logger.error(f"生成RSS失败: {exc}")
        return ""


async def generate_atom_feed(
    db: AsyncSession,
    base_url: str = "http://localhost:8000",
    limit: int = 20,
    category_id: Optional[int] = None,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """生成 Atom 1.0 订阅内容（失败时返回空串）"""
    try:
        generator = _build_generator(
            base_url=base_url, feed_path=ATOM_PATH, title=title, description=description
        )
        for item in await _load_items(
            db, base_url=base_url, limit=limit, category_id=category_id
        ):
            generator.add_item(item)
        return generator.generate_atom()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"生成Atom失败: {exc}")
        return ""


async def get_feed_metadata(db: AsyncSession) -> Dict[str, Any]:
    """Feed 元数据（文章总数与最近更新时间），供前端/SEO 展示"""
    try:
        total_articles = int(
            (
                await db.execute(
                    select(func.count(Article.id)).where(Article.status == 1)
                )
            ).scalar()
            or 0
        )
        latest = (
            await db.execute(
                select(Article.created_at)
                .where(Article.status == 1)
                .order_by(Article.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        return {
            "total_articles": total_articles,
            "latest_update": latest.isoformat() if latest else None,
            "rss_url": RSS_PATH,
            "atom_url": ATOM_PATH,
            "formats": ["rss", "atom"],
        }
    except Exception as exc:  # noqa: BLE001
        logger.error(f"获取Feed元数据失败: {exc}")
        return {
            "total_articles": 0,
            "latest_update": None,
            "rss_url": RSS_PATH,
            "atom_url": ATOM_PATH,
            "formats": ["rss", "atom"],
        }


__all__ = [
    "ATOM_PATH",
    "RSS_PATH",
    "generate_atom_feed",
    "generate_rss_feed",
    "get_feed_metadata",
]
