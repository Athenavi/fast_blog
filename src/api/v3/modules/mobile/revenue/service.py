"""mobile.revenue 模块业务逻辑（薄封装 commerce/revenue 的服务）

复用 ``commerce.revenue`` 的 ``revenue_record_service`` / ``payout_service``
（与 ``mobile/media`` 复用 ``content/media`` 的 media_service 同一做法），
差异只在「user_id 固定为登录用户」。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.modules.commerce.revenue.schema import PayoutRequestCreate
from src.api.v3.modules.commerce.revenue.service import payout_service, revenue_record_service
from src.api.v3.modules.mobile.revenue.schema import MobilePayoutCreate


class MobileRevenueService:
    """前台「我的收益」"""

    async def list_records(
        self, db: AsyncSession, user_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        return await revenue_record_service.list_records(
            db, page=page, page_size=page_size, user_id=user_id
        )

    async def summary(self, db: AsyncSession, user_id: int) -> dict:
        return await revenue_record_service.user_summary(db, user_id)

    async def create_payout(
        self, db: AsyncSession, user_id: int, payload: MobilePayoutCreate
    ) -> dict:
        # user_id 强制为登录用户，忽略任何外部传入的可能
        return await payout_service.create_payout(
            db, PayoutRequestCreate(user_id=user_id, **payload.model_dump())
        )


mobile_revenue_service = MobileRevenueService()
