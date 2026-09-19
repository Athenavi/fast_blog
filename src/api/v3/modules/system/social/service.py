"""social 模块业务逻辑：用户社交账号绑定（OAuthAccount）"""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import OAuthAccount
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.system.social.schema import OAuthAccountOut


def _to_out(row) -> dict:
    data = OAuthAccountOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["has_token"] = bool(getattr(row, "access_token", None))
    return data


class SocialService:
    """社交账号绑定管理（system 域）"""

    async def list_accounts(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        user_id: Optional[int] = None, provider: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        stmt = select(OAuthAccount).order_by(OAuthAccount.id.desc())
        count_stmt = select(func.count()).select_from(OAuthAccount)
        if user_id is not None:
            stmt = stmt.where(OAuthAccount.user_id == user_id)
            count_stmt = count_stmt.where(OAuthAccount.user_id == user_id)
        if provider:
            stmt = stmt.where(OAuthAccount.provider == provider)
            count_stmt = count_stmt.where(OAuthAccount.provider == provider)
        total = (await db.execute(count_stmt)).scalar() or 0
        rows = (await db.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return [_to_out(r) for r in rows], int(total)

    async def delete_binding(self, db: AsyncSession, account_id: int) -> None:
        row = await oauth_account_crud.get(db, account_id)
        if row is None:
            raise NotFoundError("绑定不存在")
        await oauth_account_crud.remove(db, row)


social_service = SocialService()
