"""dashboard 模块业务逻辑

聚合查询全部走 ``func.count`` / ``func.sum`` / ``func.date``，不拉全表到应用层；
天数范围做上限保护，避免被构造出超大区间查询。
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.category.category import Category
from shared.models.comment.comment import Comment
from shared.models.media.media import Media
from shared.models.user import User
from src.api.v3.core.logger import get_logger

logger = get_logger("dashboard")

STATUS_DELETED = -1
STATUS_DRAFT = 0
STATUS_PUBLISHED = 1

MAX_TREND_DAYS = 365


class DashboardService:
    """后台数据概览"""

    async def _count(self, db: AsyncSession, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await db.execute(stmt)).scalar() or 0)

    async def overview(self, db: AsyncSession) -> dict:
        active = Article.status != STATUS_DELETED

        total_articles = await self._count(db, Article, active)
        published = await self._count(db, Article, Article.status == STATUS_PUBLISHED)
        drafts = await self._count(db, Article, Article.status == STATUS_DRAFT)

        total_users = await self._count(db, User)
        active_users = await self._count(db, User, User.is_active.is_(True))

        total_comments = await self._count(db, Comment)
        pending_comments = await self._count(db, Comment, Comment.is_approved.is_(False))

        views = (
                    await db.execute(select(func.coalesce(func.sum(Article.views), 0)).where(active))
                ).scalar() or 0
        likes = (
                    await db.execute(select(func.coalesce(func.sum(Article.likes), 0)).where(active))
                ).scalar() or 0

        return {
            "total_articles": total_articles,
            "published_articles": published,
            "draft_articles": drafts,
            "total_users": total_users,
            "active_users": active_users,
            "total_comments": total_comments,
            "pending_comments": pending_comments,
            "total_views": int(views),
            "total_likes": int(likes),
            "total_categories": await self._count(db, Category),
            "total_media": await self._count(db, Media),
        }

    async def trend(self, db: AsyncSession, *, days: int = 30) -> dict:
        """最近 N 天的新增文章 / 评论 / 用户（按自然日聚合）"""
        days = max(1, min(int(days), MAX_TREND_DAYS))
        since = datetime.now() - timedelta(days=days - 1)

        async def _by_day(model, date_column, *conditions) -> dict[str, int]:
            stmt = (
                select(func.date(date_column).label("day"), func.count())
                .where(date_column >= since, *conditions)
                .group_by(func.date(date_column))
            )
            return {
                str(day): int(count or 0)
                for day, count in (await db.execute(stmt)).all()
                if day is not None
            }

        articles = await _by_day(Article, Article.created_at, Article.status != STATUS_DELETED)
        comments = await _by_day(Comment, Comment.created_at)
        users = await _by_day(User, User.date_joined)

        points = []
        for offset in range(days):
            day = (since + timedelta(days=offset)).date().isoformat()
            points.append(
                {
                    "day": day,
                    "articles": articles.get(day, 0),
                    "comments": comments.get(day, 0),
                    "users": users.get(day, 0),
                }
            )
        return {"days": days, "points": points}

    async def recent_articles(self, db: AsyncSession, *, limit: int = 5) -> List[dict]:
        stmt = (
            select(Article)
            .where(Article.status != STATUS_DELETED)
            .order_by(Article.created_at.desc(), Article.id.desc())
            .limit(max(1, min(limit, 50)))
        )
        return [
            {
                "id": article.id,
                "title": article.title,
                "slug": article.slug,
                "status": article.status,
                "views": article.views or 0,
                "created_at": article.created_at,
                "published_at": article.published_at,
            }
            for article in (await db.execute(stmt)).scalars().all()
        ]

    async def recent_comments(self, db: AsyncSession, *, limit: int = 5) -> List[dict]:
        stmt = select(Comment).order_by(Comment.created_at.desc(), Comment.id.desc()).limit(
            max(1, min(limit, 50))
        )
        return [
            {
                "id": comment.id,
                "article_id": comment.article_id,
                "content": comment.content,
                "author_name": comment.author_name,
                "is_approved": bool(comment.is_approved),
                "created_at": comment.created_at,
            }
            for comment in (await db.execute(stmt)).scalars().all()
        ]

    async def top_articles(
        self, db: AsyncSession, *, limit: int = 10, days: Optional[int] = None
    ) -> List[dict]:
        """按浏览量排行（可按最近 N 天过滤创建时间）"""
        stmt = select(Article).where(Article.status == STATUS_PUBLISHED)
        if days:
            days = max(1, min(int(days), MAX_TREND_DAYS))
            stmt = stmt.where(Article.created_at >= datetime.now() - timedelta(days=days))
        stmt = stmt.order_by(Article.views.desc(), Article.id.desc()).limit(max(1, min(limit, 100)))
        return [
            {
                "id": article.id,
                "title": article.title,
                "views": article.views or 0,
                "likes": article.likes or 0,
            }
            for article in (await db.execute(stmt)).scalars().all()
        ]


dashboard_service = DashboardService()
