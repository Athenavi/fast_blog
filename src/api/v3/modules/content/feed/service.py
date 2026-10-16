"""动态流：关注时间线 / 发现流 / 用户公开动态（真表聚合）

v2 的 ``PersonalizedFeedService``（8.5KB）把关注关系与事件全放在**进程内存**
（``defaultdict`` + ``_events`` dict，代码注释自承"后续应迁移到数据库表"）；
v3 全部从真表算：

  - 关注关系：``user_follows``（真表）。关注 / 取关 / 粉丝列表由 ``mobile/follow`` 提供，
    本模块**不重复实现**，只做「流」的聚合
  - 事件源：``articles``（关注的人发布）+ ``article_likes``（关注的人点赞）+ ``comments``（关注的人评论）
  - 事件统一成 ``{type, at, actor, article, extra}``，用 ``UNION ALL`` 在库内排序分页
    （不是"各查一批再在 Python 里拼" —— 那样分页会不准）

**不做**：事件流的持久化物化（``feed_events`` 表 + 写入扇出）—— 那需要额外的写入链路与
容量治理，本批先从真表实时聚合，规模上来再谈物化。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import String, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_like import ArticleLike
from shared.models.comment.comment import Comment
from shared.models.user.user_follow import UserFollow
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("content.feed")

#: 支持的事件类型
EVENT_TYPES = ("article", "like", "comment")

#: 事件摘要长度上限
EXCERPT_LIMIT = 120


class FeedService:
    """动态流聚合"""

    # ------------------------------------------------------------------ 关注时间线
    async def timeline(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
        event_types: Optional[Sequence[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """关注的人产生的动态（新文章 / 点赞 / 评论），按时间倒序"""
        followed = list(
            (
                await db.execute(
                    select(UserFollow.following).where(UserFollow.follower == user_id)
                )
            ).scalars().all()
        )
        if not followed:
            return [], 0

        types = self._normalize_types(event_types)
        events = self._event_select(actor_ids=followed, types=types)
        return await self._page_events(db, events, page=page, page_size=page_size)

    # ------------------------------------------------------------------ 发现流
    async def discover(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        include_interactions: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """公开发现流：全站已发布文章（可选带上全站最新点赞 / 评论）"""
        types = ("article", "like", "comment") if include_interactions else ("article",)
        events = self._event_select(actor_ids=None, types=types)
        return await self._page_events(db, events, page=page, page_size=page_size)

    # ------------------------------------------------------------------ 用户公开动态
    async def user_feed(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """某个用户的公开动态：他发布的文章 + 他通过审核的评论"""
        await self._user_or_404(db, user_id)
        events = self._event_select(actor_ids=[user_id], types=("article", "comment"))
        return await self._page_events(db, events, page=page, page_size=page_size)

    # ------------------------------------------------------------------ 概览
    async def stats(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """我的流概览：关注数 / 时间线事件数 / 各类型分布"""
        following = int(
            (
                await db.execute(
                    select(func.count()).select_from(UserFollow).where(UserFollow.follower == user_id)
                )
            ).scalar()
            or 0
        )
        if not following:
            return {
                "user_id": user_id,
                "following": 0,
                "timeline_events": 0,
                "by_type": {},
                "hint": "还没有关注任何人 —— 时间线为空，可先看「发现」流",
            }

        followed = list(
            (
                await db.execute(select(UserFollow.following).where(UserFollow.follower == user_id))
            ).scalars().all()
        )
        events = self._event_select(actor_ids=followed, types=EVENT_TYPES)
        total = int(
            (await db.execute(select(func.count()).select_from(events))).scalar() or 0
        )
        rows = (
            await db.execute(
                select(events.c.event_type, func.count()).group_by(events.c.event_type)
            )
        ).all()
        return {
            "user_id": user_id,
            "following": following,
            "timeline_events": total,
            "by_type": {str(kind): int(count) for kind, count in rows},
        }

    # ------------------------------------------------------------------ 内部
    @staticmethod
    def _normalize_types(event_types: Optional[Sequence[str]]) -> Tuple[str, ...]:
        if not event_types:
            return EVENT_TYPES
        cleaned = tuple(str(item).strip().lower() for item in event_types if str(item).strip())
        unknown = [item for item in cleaned if item not in EVENT_TYPES]
        if unknown:
            raise BadRequestError(f"未知事件类型：{unknown}（可选：{list(EVENT_TYPES)}）")
        return cleaned or EVENT_TYPES

    @staticmethod
    def _event_select(*, actor_ids: Optional[Sequence[int]], types: Sequence[str]):
        """构造 ``UNION ALL`` 事件查询（列：event_type / at / actor_id / article_id / extra）

        始终返回 **subquery**（各部分内部先按 actor 过滤再 UNION，比外层过滤更省），
        这样分页与计数都在库内完成。
        """
        actors = list(actor_ids) if actor_ids is not None else None
        parts = []
        if "article" in types:
            stmt = select(
                literal("article", String).label("event_type"),
                Article.published_at.label("at"),
                Article.user.label("actor_id"),
                Article.id.label("article_id"),
                literal(None, String).label("extra"),
            ).where(Article.status == 1, Article.published_at.isnot(None))
            if actors is not None:
                stmt = stmt.where(Article.user.in_(actors))
            parts.append(stmt)
        if "like" in types:
            stmt = select(
                literal("like", String).label("event_type"),
                ArticleLike.created_at.label("at"),
                ArticleLike.user.label("actor_id"),
                ArticleLike.article.label("article_id"),
                literal(None, String).label("extra"),
            )
            if actors is not None:
                stmt = stmt.where(ArticleLike.user.in_(actors))
            parts.append(stmt)
        if "comment" in types:
            stmt = select(
                literal("comment", String).label("event_type"),
                Comment.created_at.label("at"),
                Comment.user_id.label("actor_id"),
                Comment.article_id.label("article_id"),
                func.substr(Comment.content, 1, EXCERPT_LIMIT).label("extra"),
            ).where(Comment.user_id.isnot(None), Comment.is_approved.is_(True))
            if actors is not None:
                stmt = stmt.where(Comment.user_id.in_(actors))
            parts.append(stmt)

        if not parts:
            raise BadRequestError("至少要选择一种事件类型")

        combined = parts[0] if len(parts) == 1 else union_all(*parts)
        return combined.subquery()

    async def _page_events(
        self, db: AsyncSession, events, *, page: int, page_size: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        total = int((await db.execute(select(func.count()).select_from(events))).scalar() or 0)
        rows = (
            await db.execute(
                select(events)
                .order_by(events.c.at.desc().nullslast(), events.c.article_id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).mappings().all()
        if not rows:
            return [], total

        article_ids = [int(row["article_id"]) for row in rows if row["article_id"] is not None]
        articles = {
            int(row.id): row
            for row in (
                await db.execute(select(Article).where(Article.id.in_(article_ids)))
            ).scalars().all()
        } if article_ids else {}

        items = []
        for row in rows:
            article = articles.get(int(row["article_id"])) if row["article_id"] is not None else None
            items.append(
                {
                    "type": row["event_type"],
                    "at": row["at"].isoformat() if isinstance(row["at"], datetime) else None,
                    "actor_id": row["actor_id"],
                    "extra": row["extra"],
                    "article": self._article_out(article) if article is not None else None,
                }
            )
        return items, total

    @staticmethod
    async def _user_or_404(db: AsyncSession, user_id: int) -> int:
        from shared.models.user import User

        row = await db.get(User, user_id)
        if row is None:
            raise NotFoundError("用户不存在")
        return int(row.id)

    @staticmethod
    def _article_out(row: Article) -> Dict[str, Any]:
        return {
            "id": int(row.id),
            "title": row.title,
            "slug": row.slug,
            "excerpt": row.excerpt,
            "user": row.user,
            "category": row.category,
            "views": int(row.views or 0),
            "likes": int(row.likes or 0),
            "published_at": row.published_at.isoformat() if row.published_at else None,
        }


feed_service = FeedService()
