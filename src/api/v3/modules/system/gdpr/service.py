"""gdpr 模块业务逻辑：合规同意记录（GDPR）"""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.security import GDPRConsent
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.system.gdpr.schema import GDPRConsentOut, GDPRStatsOut

GDPR_MODEL = GDPRConsent


def _to_out(row) -> dict:
    return GDPRConsentOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class GDPRService:
    """合规同意记录（system 域）"""

    async def list_consents(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        user_id: Optional[int] = None, consent_type: Optional[str] = None,
        granted: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        stmt = select(GDPR_MODEL).order_by(GDPR_MODEL.created_at.desc(), GDPR_MODEL.id.desc())
        count_stmt = select(func.count()).select_from(GDPR_MODEL)
        if user_id is not None:
            stmt = stmt.where(GDPR_MODEL.user_id == user_id)
            count_stmt = count_stmt.where(GDPR_MODEL.user_id == user_id)
        if consent_type:
            stmt = stmt.where(GDPR_MODEL.consent_type == consent_type)
            count_stmt = count_stmt.where(GDPR_MODEL.consent_type == consent_type)
        if granted is not None:
            stmt = stmt.where(GDPR_MODEL.granted.is_(granted))
            count_stmt = count_stmt.where(GDPR_MODEL.granted.is_(granted))
        total = (await db.execute(count_stmt)).scalar() or 0
        rows = (await db.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return [_to_out(r) for r in rows], int(total)

    async def stats(self, db: AsyncSession) -> dict:
        total = (await db.execute(select(func.count()).select_from(GDPR_MODEL))).scalar() or 0
        granted = (await db.execute(
            select(func.count()).select_from(GDPR_MODEL).where(GDPR_MODEL.granted.is_(True))
        )).scalar() or 0
        rows = (await db.execute(
            select(GDPR_MODEL.consent_type, func.count())
            .group_by(GDPR_MODEL.consent_type)
        )).all()
        return GDPRStatsOut(
            total=int(total),
            granted=int(granted),
            revoked=int(total) - int(granted),
            by_type={(t or 'unknown'): int(n) for t, n in rows},
        ).model_dump()

    async def delete_consent(self, db: AsyncSession, consent_id: int) -> None:
        row = await db.get(GDPR_MODEL, consent_id)
        if row is None:
            raise NotFoundError("记录不存在")
        await db.delete(row)
        await db.commit()


gdpr_service = GDPRService()
