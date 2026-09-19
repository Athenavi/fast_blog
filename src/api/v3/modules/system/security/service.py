"""security 模块业务逻辑：安全中心聚合（登录尝试 / 锁定账户 / 令牌黑名单）"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.security import LoginAttempt, TokenBlacklist
from shared.services.users.login_security_service import login_security_service
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.system.security.schema import (
    BlacklistOut,
    LoginAttemptOut,
    SecurityOverviewOut,
)


def _attempt_out(row) -> dict:
    return LoginAttemptOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _blacklist_out(row) -> dict:
    return BlacklistOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class SecurityService:
    """安全中心（system 域，聚合既有安全表与服务）"""

    async def overview(self, db: AsyncSession) -> dict:
        cutoff = datetime.now() - timedelta(hours=24)
        attempts_24h = (await db.execute(
            select(func.count()).select_from(LoginAttempt).where(LoginAttempt.created_at >= cutoff)
        )).scalar() or 0
        failures_24h = (await db.execute(
            select(func.count()).select_from(LoginAttempt)
            .where(LoginAttempt.created_at >= cutoff, LoginAttempt.is_success.is_(False))
        )).scalar() or 0
        reasons = (await db.execute(
            select(LoginAttempt.failure_reason, func.count())
            .where(LoginAttempt.created_at >= cutoff, LoginAttempt.is_success.is_(False))
            .group_by(LoginAttempt.failure_reason)
            .order_by(func.count().desc())
            .limit(5)
        )).all()
        locked = await login_security_service.get_locked_users_async(db)
        blacklist_count = (await db.execute(
            select(func.count()).select_from(TokenBlacklist).where(
                TokenBlacklist.expires_at.is_(None) | (TokenBlacklist.expires_at > datetime.now())
            )
        )).scalar() or 0
        success_rate = round((attempts_24h - failures_24h) / attempts_24h * 100, 1) if attempts_24h else 100.0
        return SecurityOverviewOut(
            attempts_24h=int(attempts_24h),
            failures_24h=int(failures_24h),
            success_rate=success_rate,
            locked_users=len(locked),
            blacklist_count=int(blacklist_count),
            top_failure_reasons={(r or 'unknown'): int(n) for r, n in reasons},
        ).model_dump()

    async def list_attempts(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        username: Optional[str] = None, is_success: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        stmt = select(LoginAttempt).order_by(LoginAttempt.created_at.desc(), LoginAttempt.id.desc())
        count_stmt = select(func.count()).select_from(LoginAttempt)
        if username:
            stmt = stmt.where(LoginAttempt.username.like(f"%{username}%"))
            count_stmt = count_stmt.where(LoginAttempt.username.like(f"%{username}%"))
        if is_success is not None:
            stmt = stmt.where(LoginAttempt.is_success.is_(is_success))
            count_stmt = count_stmt.where(LoginAttempt.is_success.is_(is_success))
        total = (await db.execute(count_stmt)).scalar() or 0
        rows = (await db.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return [_attempt_out(r) for r in rows], int(total)

    async def list_blacklist(self, db: AsyncSession, *, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        rows, total = await token_blacklist_crud.list(db, page=page, page_size=page_size)
        return [_blacklist_out(r) for r in rows], total

    async def delete_blacklist(self, db: AsyncSession, entry_id: int) -> None:
        row = await token_blacklist_crud.get(db, entry_id)
        if row is None:
            raise NotFoundError("记录不存在")
        await token_blacklist_crud.remove(db, row)


security_service = SecurityService()
