"""mobile/user 业务逻辑"""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.comment.comment import Comment
from shared.models.user import User as UserModel
from shared.services.users.user_manager import set_user_password, update_user_profile
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.mobile.user.schema import MobileProfileUpdate
from src.api.v3.modules.system.auth.service import auth_service

logger = get_logger("mobile.user")

STATUS_DELETED = -1


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


mobile_user_service = MobileUserService()
