"""mobile/user 业务逻辑"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.certification import ExpertCertification
from shared.models.comment.comment import Comment
from shared.models.user import User as UserModel
from shared.models.user.user_follow import UserFollow
from shared.services.users.user_manager import set_user_password, update_user_profile
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.mobile.user.schema import (
    MobileProfileUpdate,
    MobilePublicProfile,
    MobilePublicProfileStats,
)
from src.api.v3.modules.system.auth.service import auth_service

logger = get_logger("mobile.user")

STATUS_DELETED = -1
STATUS_PUBLISHED = 1

#: 公开主页绝不允许出现的敏感 / 权限字段（供测试与审查核对）
SENSITIVE_FIELDS = (
    "email",
    "password",
    "totp_secret",
    "backup_codes",
    "last_login_ip",
    "register_ip",
    "is_superuser",
    "is_staff",
)


def build_public_profile(
    user: object,
    *,
    is_following: bool = False,
    is_mutual: bool = False,
    is_certified: bool = False,
    stats: Optional[dict] = None,
) -> dict:
    """把 User 行 + 关注标记 + 统计拼成公开主页响应（纯函数，便于用假对象测试）。

    只暴露白名单字段：``profile_private`` 为真时仅保留 id / username / profile_picture，
    其余为 null / 0 / false，``bio`` 与 ``stats`` 不泄露真实内容。
    """
    is_private = getattr(user, "profile_private", None) is True
    counts = stats or {}
    if is_private:
        return MobilePublicProfile(
            id=int(user.id),  # type: ignore[attr-defined]
            username=getattr(user, "username", None),
            profile_picture=getattr(user, "profile_picture", None),
            is_private=True,
        ).model_dump(mode="json")
    return MobilePublicProfile(
        id=int(user.id),  # type: ignore[attr-defined]
        username=getattr(user, "username", None),
        profile_picture=getattr(user, "profile_picture", None),
        bio=getattr(user, "bio", None),
        vip_level=int(getattr(user, "vip_level", 0) or 0),
        date_joined=getattr(user, "date_joined", None),
        is_private=False,
        is_following=is_following,
        is_mutual=is_mutual,
        is_certified=is_certified,
        stats=MobilePublicProfileStats(
            articles=int(counts.get("articles", 0)),
            followers=int(counts.get("followers", 0)),
            following=int(counts.get("following", 0)),
        ),
    ).model_dump(mode="json")


class MobileUserService:
    """移动端个人中心"""

    async def profile(self, db: AsyncSession, user: UserModel) -> dict:
        return await auth_service.build_current_user(db, user)

    async def update_profile(
        self, db: AsyncSession, user: UserModel, payload: MobileProfileUpdate
    ) -> dict:
        data = payload.model_dump(exclude_unset=True)
        password: Optional[str] = data.pop("password", None)

        if data:
            await update_user_profile(db, user.id, **data)
        if password:
            await set_user_password(db, user.id, password)

        await db.commit()
        await db.refresh(user)
        return await auth_service.build_current_user(db, user)

    async def stats(self, db: AsyncSession, user_id: int) -> dict:
        articles = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(Article)
                    .where(Article.user == user_id, Article.status != STATUS_DELETED)
                )
            ).scalar()
            or 0
        )
        comments = int(
            (
                await db.execute(
                    select(func.count()).select_from(Comment).where(Comment.user_id == user_id)
                )
            ).scalar()
            or 0
        )
        likes = (
                    await db.execute(
                        select(func.coalesce(func.sum(Article.likes), 0)).where(
                            Article.user == user_id, Article.status != STATUS_DELETED
                        )
                    )
                ).scalar() or 0
        return {"articles": articles, "comments": comments, "likes_received": int(likes)}

    # ------------------------------------------------------------ 公开主页

    async def _count(self, db: AsyncSession, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await db.execute(stmt)).scalar() or 0)

    async def _is_following(self, db: AsyncSession, follower: int, following: int) -> bool:
        return (
            await self._count(
                db,
                UserFollow,
                UserFollow.follower == follower,
                UserFollow.following == following,
            )
            > 0
        )

    async def _is_certified(self, db: AsyncSession, user_id: int) -> bool:
        """``expert_certifications``：status == 'approved' 且未过期（参考 certification/service.py）"""
        now = datetime.now()
        row = (
            await db.execute(
                select(ExpertCertification.id)
                .where(
                    ExpertCertification.user_id == user_id,
                    ExpertCertification.status == "approved",
                    (ExpertCertification.expires_at.is_(None))
                    | (ExpertCertification.expires_at > now),
                )
                .limit(1)
            )
        ).first()
        return row is not None

    async def public_profile(
        self, db: AsyncSession, username: str, viewer_id: Optional[int] = None
    ) -> dict:
        """用户公开主页（公开，允许匿名；登录时额外给关注标记）。

        - 用户不存在或 ``is_active`` 为假 → 404；
        - ``profile_private`` 为真 → 只返回 id / username / profile_picture（其余空）；
        - 绝不返回 email / password / 密钥等敏感字段。
        """
        user = (
            await db.execute(select(UserModel).where(UserModel.username == username))
        ).scalars().first()
        if user is None or not bool(getattr(user, "is_active", True)):
            raise NotFoundError("用户不存在")

        # 私密资料：不泄露 bio 与统计
        if getattr(user, "profile_private", None) is True:
            return build_public_profile(user)

        is_following = is_mutual = False
        if viewer_id is not None and viewer_id != user.id:
            is_following = await self._is_following(db, viewer_id, user.id)
            if is_following:
                is_mutual = await self._is_following(db, user.id, viewer_id)

        stats = {
            "articles": await self._count(
                db,
                Article,
                Article.user == user.id,
                Article.status == STATUS_PUBLISHED,
            ),
            "followers": await self._count(
                db, UserFollow, UserFollow.following == user.id
            ),
            "following": await self._count(
                db, UserFollow, UserFollow.follower == user.id
            ),
        }
        is_certified = await self._is_certified(db, user.id)

        return build_public_profile(
            user,
            is_following=is_following,
            is_mutual=is_mutual,
            is_certified=is_certified,
            stats=stats,
        )


mobile_user_service = MobileUserService()
