"""follow 模块业务逻辑（前台关注关系）

**与 v2 的差异**（v2 的 6 个关注端点在 ``users/unified_users.py`` 里）：

| v2 的做法 | 问题 | 本模块 |
|---|---|---|
| 读写**模块级内存字典** ``followers_db`` / ``follows_db`` | 重启即丢、多 worker 各一份（注释自承"后续应迁移到数据库表"） | 真表 ``user_follows`` |
| 关注时**不校验目标用户是否存在** | 可关注一个不存在的 ID，产生幽灵关系 | 不存在 → 404 |
| 列表**无分页**（全量倒序返回） | 大 V 的粉丝列表直接打爆 | 分页（``page`` / ``page_size``，上限 100） |
| 不处理"被拉黑" | 被拉黑者仍能关注对方 | **对方拉黑了我 → 409** |
| 无 ``is_following`` / ``is_mutual`` | 前端要再发一轮请求才能判断 | 列表与概览都带这两个标记（**批量查询**，不 N+1） |
| 取关无存在性校验 | 恒返回成功 | 幂等（不存在也返回成功，但目标用户要先存在） |
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User, UserBlock
from shared.models.user.user_follow import UserFollow
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.modules.mobile.follow.crud import user_follow_crud
from src.api.v3.modules.mobile.follow.schema import FollowStats, FollowUserBrief

MAX_PAGE_SIZE = 100


def _brief(user: User, *, is_following: bool = False, is_mutual: bool = False) -> dict:
    return FollowUserBrief(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=bool(getattr(user, "is_active", True)),
        created_at=getattr(user, "date_joined", None),
        is_following=is_following,
        is_mutual=is_mutual,
    ).model_dump(mode="json")


class FollowService:
    """关注关系"""

    async def _ensure_user(self, db: AsyncSession, user_id: int) -> User:
        user = await db.get(User, user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        return user

    async def _count(self, db: AsyncSession, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await db.execute(stmt)).scalar() or 0)

    async def _is_blocked_by(
        self, db: AsyncSession, target_id: int, viewer_id: Optional[int]
    ) -> bool:
        """``target`` 是否拉黑了 ``viewer``"""
        if viewer_id is None:
            return False
        return (
            await self._count(
                db,
                UserBlock,
                UserBlock.blocker == target_id,
                UserBlock.blocked_user == viewer_id,
            )
            > 0
        )

    async def _follow_flags(
        self, db: AsyncSession, user_ids: list[int], viewer_id: Optional[int]
    ) -> dict[int, tuple[bool, bool]]:
        """批量算 ``(is_following, is_mutual)`` —— 两次查询，不做 N+1"""
        if not user_ids or viewer_id is None:
            return {}
        following = set(
            (
                await db.execute(
                    select(UserFollow.following).where(
                        UserFollow.follower == viewer_id, UserFollow.following.in_(user_ids)
                    )
                )
            ).scalars().all()
        )
        followers = set(
            (
                await db.execute(
                    select(UserFollow.follower).where(
                        UserFollow.following == viewer_id, UserFollow.follower.in_(user_ids)
                    )
                )
            ).scalars().all()
        )
        return {
            uid: (uid in following, uid in following and uid in followers) for uid in user_ids
        }

    async def _list(
        self,
        db: AsyncSession,
        *,
        owner_id: int,
        viewer_id: Optional[int],
        direction: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """``direction='follower'`` 查 owner 的粉丝；``'following'`` 查 owner 关注的人"""
        await self._ensure_user(db, owner_id)
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
        if direction == "follower":
            condition = UserFollow.following == owner_id
            peer_column = UserFollow.follower
        else:
            condition = UserFollow.follower == owner_id
            peer_column = UserFollow.following

        total = await self._count(db, UserFollow, condition)
        rows = (
            await db.execute(
                select(UserFollow, User)
                .join(User, User.id == peer_column)
                .where(condition)
                .order_by(UserFollow.created_at.desc(), UserFollow.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        peer_ids = [user.id for _link, user in rows]
        flags = await self._follow_flags(db, peer_ids, viewer_id)
        items = [
            {
                "user": _brief(user, *flags.get(user.id, (False, False))),
                "created_at": link.created_at,
            }
            for link, user in rows
        ]
        return items, total

    async def follower_list(self, db: AsyncSession, **kwargs) -> tuple[list[dict], int]:
        return await self._list(db, direction="follower", **kwargs)

    async def following_list(self, db: AsyncSession, **kwargs) -> tuple[list[dict], int]:
        return await self._list(db, direction="following", **kwargs)

    async def stats(
        self, db: AsyncSession, user_id: int, viewer_id: Optional[int] = None
    ) -> dict:
        """某个用户的关注概览（含"我是否关注 / 是否互关"）"""
        await self._ensure_user(db, user_id)
        follower_count = await self._count(db, UserFollow, UserFollow.following == user_id)
        following_count = await self._count(db, UserFollow, UserFollow.follower == user_id)
        is_following = is_mutual = False
        if viewer_id is not None and viewer_id != user_id:
            is_following, is_mutual = (await self._follow_flags(db, [user_id], viewer_id)).get(
                user_id, (False, False)
            )
        return FollowStats(
            user_id=user_id,
            follower_count=follower_count,
            following_count=following_count,
            is_following=is_following,
            is_mutual=is_mutual,
        ).model_dump(mode="json")

    async def follow(self, db: AsyncSession, target_id: int, current_user_id: int) -> dict:
        if target_id == current_user_id:
            raise BadRequestError("不能关注自己")
        await self._ensure_user(db, target_id)
        if await self._is_blocked_by(db, target_id, current_user_id):
            raise ConflictError("对方已拉黑你，无法关注")
        existing = await user_follow_crud.get_by(
            db, follower=current_user_id, following=target_id
        )
        if existing is None:
            await user_follow_crud.create(
                db,
                {
                    "follower": current_user_id,
                    "following": target_id,
                    "created_at": datetime.now(),
                },
            )
        return await self.stats(db, target_id, current_user_id)

    async def unfollow(self, db: AsyncSession, target_id: int, current_user_id: int) -> dict:
        await self._ensure_user(db, target_id)
        existing = await user_follow_crud.get_by(
            db, follower=current_user_id, following=target_id
        )
        if existing is not None:
            await user_follow_crud.remove(db, existing)
        return await self.stats(db, target_id, current_user_id)


follow_service = FollowService()
