"""feed 模块业务逻辑（关注流 personalized feed）

**与 v2 的差异**：v2 没有真实的关注流——前台「动态」要么直接列全站文章，要么读一个
模块级内存的假关注列表。本模块按登录用户的**真实**关注关系聚合文章：

1. 取 ``user_follows`` 里 ``follower == 登录用户`` 的 ``following`` 集合；
2. 交给 ``article_service.public_list`` 的 ``user_ids`` 过滤，复用公开列表的排序与
   「只含已发布」口径（置顶 → ``sort_order`` → 发布时间倒序）；
3. **关注为空 → 直接返回空页**（既不是报错，也**不**退化成全站文章）。

``IN (...)`` 规模保护：一次关注的人数超过 ``MAX_FOLLOWING_IDS``（500）时，按
「最近关注的优先」截断到 500 并记 warning。选择**截断**而非分批，是为了保持
分页 / ``total`` 语义简单——分批后需要跨批排序再切片，收益不大且易错。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user.user_follow import UserFollow
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.content.article.service import article_service

logger = get_logger("mobile.feed")

#: 单次聚合参与 ``IN (...)`` 的关注人数上限
MAX_FOLLOWING_IDS = 500
#: 与前端 / 契约一致的分页上限
MAX_PAGE_SIZE = 50


class FeedService:
    """关注流"""

    async def following_ids(self, db: AsyncSession, user_id: int) -> list[int]:
        """当前用户关注的人的 id（最近关注优先；超过上限则截断并记日志）"""
        rows = (
            (
                await db.execute(
                    select(UserFollow.following)
                    .where(UserFollow.follower == user_id)
                    .order_by(UserFollow.created_at.desc(), UserFollow.id.desc())
                    .limit(MAX_FOLLOWING_IDS + 1)
                )
            )
            .scalars()
            .all()
        )
        ids = list(rows)
        if len(ids) > MAX_FOLLOWING_IDS:
            logger.warning(
                "关注流聚合：用户 %s 关注人数超过 %d，按最近关注截断",
                user_id,
                MAX_FOLLOWING_IDS,
            )
            ids = ids[:MAX_FOLLOWING_IDS]
        return ids

    async def list_feed(
        self, db: AsyncSession, user_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        """关注流分页；关注为空时返回空页（不退化成全站文章）"""
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
        ids = await self.following_ids(db, user_id)
        if not ids:
            return [], 0
        return await article_service.public_list(
            db, page=page, page_size=page_size, user_ids=ids
        )


feed_service = FeedService()
