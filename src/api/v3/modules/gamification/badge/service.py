"""badge 模块业务逻辑（勋章定义 / 授予 / 真实统计源）

**与 v2 的差异**（v2 在 `services/advanced_features/achievement_badges.py`）：

| v2 的做法 | 问题 | 本模块 |
|---|---|---|
| 18 个内置徽章是**类内常量** | 改勋章要改代码 | 定义入库（``badge_definitions``），用 seed 脚本灌入 |
| ``_get_user_stats`` **直接返回全 0**（真查询被注释掉） | ``check-and-award`` **永远授予不了** | 统计全部取自真实表（见 ``_stats``） |
| 授予写内存字典 | 重启即失 | 写 ``user_badges``（``(user_id, badge_key)`` 唯一 → 授予幂等） |
| 授予不联动积分 | 奖励形同虚设 | 授予时通过 ``points_service.award`` 真实发放 ``points_reward`` |

统计口径：文章数 / 单篇最高获赞 / 累计获赞 取自 ``articles``（作者列是 **``user``**）；
评论数取自 ``comments``（作者列是 **``user_id``**，与 articles 不同）；粉丝数取自
``user_follows``（批次 11 新建）。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.comment.comment import Comment
from shared.models.gamification import BadgeDefinition, UserBadge
from shared.models.user import User
from shared.models.user.user_follow import UserFollow
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.gamification.badge.crud import badge_definition_crud, user_badge_crud
from src.api.v3.modules.gamification.badge.schema import (
    CONDITION_TYPES,
    BadgeAwardRequest,
    BadgeOut,
    UserBadgeOut,
)
from src.api.v3.modules.gamification.points.service import points_service

logger = get_logger("gamification.badge")

STATUS_PUBLISHED = 1
STATUS_DELETED = -1
MAX_PAGE_SIZE = 200


def _definition_out(row: BadgeDefinition) -> dict:
    return BadgeOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _user_badge_out(record: UserBadge, definition: Optional[BadgeDefinition]) -> dict:
    return UserBadgeOut(
        badge_key=record.badge_key,
        name=getattr(definition, "name", None),
        description=getattr(definition, "description", None),
        category=getattr(definition, "category", None),
        icon=getattr(definition, "icon", None),
        points_reward=int(getattr(definition, "points_reward", 0) or 0),
        awarded_at=record.awarded_at,
        awarded_by=record.awarded_by,
    ).model_dump(mode="json")


class BadgeService:
    """勋章"""

    # ------------------------------------------------------------ 真实统计
    async def _count(self, db: AsyncSession, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await db.execute(stmt)).scalar() or 0)

    async def _stats(self, db: AsyncSession, user_id: int) -> dict:
        """勋章条件用的用户统计 —— **全部来自真实表**（v2 这里是写死的 0）"""
        mine = Article.user == user_id
        published = Article.status == STATUS_PUBLISHED

        article_count = await self._count(db, Article, mine, published)
        max_likes = int(
            (
                await db.execute(
                    select(func.coalesce(func.max(Article.likes), 0)).where(mine, published)
                )
            ).scalar()
            or 0
        )
        like_received = int(
            (
                await db.execute(
                    select(func.coalesce(func.sum(Article.likes), 0)).where(mine, published)
                )
            ).scalar()
            or 0
        )
        follower_count = await self._count(db, UserFollow, UserFollow.following == user_id)
        comment_count = await self._count(db, Comment, Comment.user_id == user_id)
        return {
            "article_count": article_count,
            "max_article_likes": max_likes,
            "follower_count": follower_count,
            "comment_count": comment_count,
            "like_received": like_received,
        }

    # ------------------------------------------------------------ 查询
    async def _definitions(self, db: AsyncSession, *, only_active: bool = True) -> list[BadgeDefinition]:
        rows, _total = await badge_definition_crud.list(db, page=1, page_size=0)
        items = [row for row in rows if (not only_active or row.is_active)]
        return sorted(items, key=lambda row: (row.sort_order or 0, row.id))

    async def _owned(self, db: AsyncSession, user_id: int) -> dict[str, UserBadge]:
        rows, _total = await user_badge_crud.list(
            db, page=1, page_size=0, filters={"user_id": user_id}
        )
        return {row.badge_key: row for row in rows}

    async def available(self, db: AsyncSession, *, category: Optional[str] = None) -> list[dict]:
        """全部可获得勋章（公开）"""
        definitions = await self._definitions(db)
        return [
            _definition_out(row)
            for row in definitions
            if not category or row.category == category
        ]

    async def categories(self, db: AsyncSession) -> list[dict]:
        """按分类聚合（公开）"""
        definitions = await self._definitions(db)
        buckets: dict[str, int] = {}
        for row in definitions:
            key = row.category or "other"
            buckets[key] = buckets.get(key, 0) + 1
        return [{"category": key, "count": count} for key, count in sorted(buckets.items())]

    async def details(self, db: AsyncSession, badge_key: str) -> dict:
        row = await badge_definition_crud.get_by(db, badge_key=badge_key)
        if row is None:
            raise NotFoundError("勋章不存在")
        return _definition_out(row)

    async def user_badges(self, db: AsyncSession, user_id: int) -> list[dict]:
        """某人已获得的勋章（带定义信息）"""
        owned = await self._owned(db, user_id)
        if not owned:
            return []
        definitions = {row.badge_key: row for row in await self._definitions(db, only_active=False)}
        records = sorted(
            owned.values(), key=lambda row: (row.awarded_at or datetime.min), reverse=True
        )
        return [_user_badge_out(record, definitions.get(record.badge_key)) for record in records]

    async def progress(self, db: AsyncSession, user_id: int, badge_key: str) -> dict:
        definition = await badge_definition_crud.get_by(db, badge_key=badge_key)
        if definition is None:
            raise NotFoundError("勋章不存在")
        owned = await self._owned(db, user_id)
        return (await self._progress_rows(db, user_id, [definition], set(owned)))[0]

    async def _progress_rows(
        self,
        db: AsyncSession,
        user_id: int,
        definitions: list[BadgeDefinition],
        owned_keys: set[str],
    ) -> list[dict]:
        stats = await self._stats(db, user_id)
        rows: list[dict] = []
        for definition in definitions:
            condition = definition.condition_type or ""
            current = int(stats.get(condition, 0))
            target = int(definition.condition_value or 0)
            rows.append(
                {
                    "badge_key": definition.badge_key,
                    "name": definition.name,
                    "description": definition.description,
                    "category": definition.category,
                    "condition_type": condition or None,
                    "condition_value": target,
                    "current_value": current,
                    "achieved": bool(target > 0 and current >= target),
                    "progress_percent": round(min(100.0, current / target * 100), 2) if target > 0 else 0.0,
                    "awarded": definition.badge_key in owned_keys,
                }
            )
        return rows

    # ------------------------------------------------------------ 授予
    async def _grant(
        self,
        db: AsyncSession,
        user_id: int,
        definition: BadgeDefinition,
        *,
        awarded_by: Optional[int],
    ) -> dict:
        now = datetime.now()
        record = await user_badge_crud.create(
            db,
            {
                "user_id": user_id,
                "badge_key": definition.badge_key,
                "awarded_at": now,
                "awarded_by": awarded_by,
            },
        )
        reward = int(definition.points_reward or 0)
        if reward > 0:
            # 真实发放积分奖励（失败不影响已授予事实，但要记日志）
            try:
                await points_service.award(
                    db,
                    user_id,
                    amount=reward,
                    action="badge_reward",
                    description=f"获得勋章：{definition.name or definition.badge_key}",
                    reference_id=definition.id,
                    reference_type="badge",
                )
            except Exception:  # noqa: BLE001
                logger.exception("勋章积分奖励发放失败: user=%s badge=%s", user_id, definition.badge_key)
        return _user_badge_out(record, definition)

    async def check_and_award(self, db: AsyncSession, user_id: int) -> dict:
        """检查并授予（幂等）

        - 已拥有的跳过；
        - ``is_manual`` 的**不自动授予**（只记进 ``skipped_manual``）；
        - 条件阈值必须 > 0 且当前统计达标。
        """
        definitions = await self._definitions(db)
        owned = await self._owned(db, user_id)
        owned_keys = set(owned)
        awarded: list[dict] = []
        skipped_manual: list[str] = []
        stats = await self._stats(db, user_id)
        for definition in definitions:
            if definition.badge_key in owned_keys:
                continue
            if definition.is_manual:
                skipped_manual.append(definition.badge_key)
                continue
            condition = definition.condition_type or ""
            target = int(definition.condition_value or 0)
            if condition not in CONDITION_TYPES or target <= 0:
                continue
            if int(stats.get(condition, 0)) >= target:
                awarded.append(await self._grant(db, user_id, definition, awarded_by=None))
                owned_keys.add(definition.badge_key)
        return {
            "awarded": awarded,
            "skipped_manual": skipped_manual,
            "progress": await self._progress_rows(db, user_id, definitions, owned_keys),
        }

    async def award(
        self, db: AsyncSession, payload: BadgeAwardRequest, operator_id: int
    ) -> dict:
        """手工授予（管理员）—— 幂等：已授予则返回已存在的那条"""
        definition = await badge_definition_crud.get_by(db, badge_key=payload.badge_key)
        if definition is None:
            raise NotFoundError("勋章不存在")
        if not definition.is_active:
            raise BadRequestError("勋章已停用")
        if await db.get(User, payload.user_id) is None:
            raise NotFoundError("用户不存在")
        owned = await self._owned(db, payload.user_id)
        if definition.badge_key in owned:
            return _user_badge_out(owned[definition.badge_key], definition) | {"already_awarded": True}
        return await self._grant(db, payload.user_id, definition, awarded_by=operator_id)

    async def stats(self, db: AsyncSession) -> dict:
        definitions = await self._definitions(db, only_active=False)
        total_awarded = int(
            (await db.execute(select(func.count()).select_from(UserBadge))).scalar() or 0
        )
        by_category = (
            await db.execute(
                select(BadgeDefinition.category, func.count(BadgeDefinition.id))
                .group_by(BadgeDefinition.category)
                .order_by(func.count(BadgeDefinition.id).desc())
            )
        ).all()
        top_badges = (
            await db.execute(
                select(UserBadge.badge_key, func.count(UserBadge.id).label("count"))
                .group_by(UserBadge.badge_key)
                .order_by(func.count(UserBadge.id).desc())
                .limit(10)
            )
        ).all()
        names = {row.badge_key: row.name for row in definitions}
        return {
            "total_definitions": len(definitions),
            "active_definitions": sum(1 for row in definitions if row.is_active),
            "total_awarded": total_awarded,
            "by_category": [
                {"category": key or "other", "count": int(count or 0)}
                for key, count in by_category
            ],
            "top_badges": [
                {"badge_key": key, "name": names.get(key), "count": int(count or 0)}
                for key, count in top_badges
            ],
        }


badge_service = BadgeService()
