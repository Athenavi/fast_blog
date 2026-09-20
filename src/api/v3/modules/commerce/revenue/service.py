"""revenue 模块业务逻辑：收益记录 / 提现申请 / 分成配置 / 用户收益统计

业务规则（自 v2 ``ecommerce/revenue_sharing.py`` 与其服务层
``shared/services/ecommerce/revenue_sharing_service.py`` 平移，行为保持一致）：

  - **分成计算**：取该 ``revenue_type`` 的 ``revenue_sharing_configs``；没有配置时按
    **30% 平台 / 70% 创作者**兜底，两个比例各自独立相乘（与 v2 一致，不假设两者和为 100）；
  - **统计联动**：创建收益记录同时把 ``user_revenue_stats`` 的
    ``total_earnings`` / ``pending_earnings`` / ``available_balance`` 各加上创作者收益；
    删除记录时对称回滚；
  - **提现校验**：低于该类型 ``min_payout_amount``（缺省 100）或可用余额不足一律拒绝；
    创建成功后**冻结**金额（``available_balance`` 立即扣减）；
  - **状态流转**：``pending → approved → completed``，或 ``pending → rejected``（驳回退还余额）；
    ``completed`` 只能从 ``approved`` 进入；
  - 金额一律用 ``Decimal`` 运算（列是 ``Numeric(10, 2)``，混用 float 会引入精度告警/误差）；
  - 平台统计与用户汇总走 **SQL 聚合**（v2 是把全表捞进内存求和）。
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.revenue import PayoutRequest, RevenueRecord, UserRevenueStats
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.commerce.revenue.crud import (
    payout_request_crud,
    revenue_record_crud,
    revenue_sharing_config_crud,
    user_revenue_stats_crud,
)
from src.api.v3.modules.commerce.revenue.schema import (
    PayoutRequestCreate,
    PayoutRequestOut,
    RevenueRecordCreate,
    RevenueRecordOut,
    SharingConfigOut,
    SharingConfigUpdate,
    UserRevenueStatsOut,
)

logger = get_logger("commerce.revenue")

#: 合法收益类型（库列是 String，白名单在服务层校验）
REVENUE_TYPES: tuple[str, ...] = (
    "advertisement",
    "vip_subscription",
    "article_purchase",
    "donation",
    "other",
)

DEFAULT_PLATFORM_PERCENTAGE = Decimal("30.0")
DEFAULT_CREATOR_PERCENTAGE = Decimal("70.0")
DEFAULT_MIN_PAYOUT = Decimal("100.0")
CENT = Decimal("0.01")


def _money(value: Any) -> Decimal:
    """任意数值 → Decimal（None 视为 0）"""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _rounded(value: Decimal) -> Decimal:
    return value.quantize(CENT)


def _record_out(row) -> dict:
    return RevenueRecordOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _payout_out(row) -> dict:
    return PayoutRequestOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _config_out(row) -> dict:
    return SharingConfigOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _stats_out(row) -> dict:
    return UserRevenueStatsOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _assert_revenue_type(revenue_type: str) -> None:
    if revenue_type not in REVENUE_TYPES:
        raise BadRequestError(
            f"收益类型不合法: {revenue_type}（可选 {'/'.join(REVENUE_TYPES)}）"
        )


class UserStatsService:
    """用户收益统计（被收益记录与提现两端共用）"""

    async def get_or_create(self, db: AsyncSession, user_id: int) -> UserRevenueStats:
        row = await user_revenue_stats_crud.get_by(db, user_id=user_id)
        if row is not None:
            return row
        now = datetime.now()
        return await user_revenue_stats_crud.create(
            db,
            {
                "user_id": user_id,
                "total_earnings": Decimal("0"),
                "total_paid": Decimal("0"),
                "pending_earnings": Decimal("0"),
                "available_balance": Decimal("0"),
                "updated_at": now,
            },
        )

    async def apply_delta(self, db: AsyncSession, user_id: int, **deltas: Decimal) -> dict:
        """在现有统计上做增量（字段缺失按 0 处理）"""
        row = await self.get_or_create(db, user_id)
        data: dict = {"updated_at": datetime.now()}
        for field, delta in deltas.items():
            data[field] = _rounded(_money(getattr(row, field, None)) + _money(delta))
        updated = await user_revenue_stats_crud.update(db, row, data)
        return _stats_out(updated)


user_stats_service = UserStatsService()


class RevenueRecordService:
    """收益记录"""

    async def list_records(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        user_id: Optional[int] = None,
        revenue_type: Optional[str] = None,
        status: Optional[str] = None,
        reference_type: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await revenue_record_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={
                "user_id": user_id,
                "revenue_type": revenue_type,
                "status": status,
                "reference_type": reference_type,
            },
        )
        return [_record_out(r) for r in rows], total

    async def create_record(self, db: AsyncSession, payload: RevenueRecordCreate) -> dict:
        _assert_revenue_type(payload.revenue_type)
        amount = _money(payload.amount)
        config = await revenue_sharing_config_crud.get_by(db, revenue_type=payload.revenue_type)
        platform_pct = (
            _money(config.platform_percentage)
            if config is not None and config.platform_percentage is not None
            else DEFAULT_PLATFORM_PERCENTAGE
        )
        creator_pct = (
            _money(config.creator_percentage)
            if config is not None and config.creator_percentage is not None
            else DEFAULT_CREATOR_PERCENTAGE
        )
        platform_fee = _rounded(amount * platform_pct / Decimal("100"))
        creator_earnings = _rounded(amount * creator_pct / Decimal("100"))
        now = datetime.now()
        row = await revenue_record_crud.create(
            db,
            payload.model_dump(exclude={"amount"})
            | {
                "amount": _rounded(amount),
                "platform_fee": platform_fee,
                "creator_earnings": creator_earnings,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            },
        )
        # 统计联动：总收益 / 待结算 / 可用余额 各 + 创作者收益
        await user_stats_service.apply_delta(
            db,
            payload.user_id,
            total_earnings=creator_earnings,
            pending_earnings=creator_earnings,
            available_balance=creator_earnings,
        )
        return _record_out(row)

    async def delete_record(self, db: AsyncSession, record_id: int) -> None:
        """删除收益记录并**对称回滚**统计（管理端纠错用）"""
        row = await revenue_record_crud.get(db, record_id)
        if row is None:
            raise NotFoundError("收益记录不存在")
        creator_earnings = _money(row.creator_earnings)
        await revenue_record_crud.remove(db, row)
        await user_stats_service.apply_delta(
            db,
            row.user_id,
            total_earnings=-creator_earnings,
            pending_earnings=-creator_earnings,
            available_balance=-creator_earnings,
        )

    async def user_summary(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """单个用户的收益汇总（按类型分组 + 统计快照）"""
        stmt = select(
            RevenueRecord.revenue_type,
            func.count().label("count"),
            func.coalesce(func.sum(RevenueRecord.amount), 0).label("amount"),
            func.coalesce(func.sum(RevenueRecord.creator_earnings), 0).label("creator_earnings"),
            func.coalesce(func.sum(RevenueRecord.platform_fee), 0).label("platform_fee"),
        ).where(RevenueRecord.user_id == user_id)
        if start_date is not None:
            stmt = stmt.where(RevenueRecord.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(RevenueRecord.created_at <= end_date)
        rows = (await db.execute(stmt.group_by(RevenueRecord.revenue_type))).all()

        by_type = [
            {
                "revenue_type": row.revenue_type,
                "count": int(row.count or 0),
                "amount": float(_rounded(_money(row.amount))),
                "creator_earnings": float(_rounded(_money(row.creator_earnings))),
                "platform_fee": float(_rounded(_money(row.platform_fee))),
            }
            for row in rows
        ]
        stats_row = await user_revenue_stats_crud.get_by(db, user_id=user_id)
        return {
            "user_id": user_id,
            "record_count": sum(item["count"] for item in by_type),
            "total_amount": float(_rounded(sum(_money(r.amount) for r in rows))),
            "total_creator_earnings": float(
                _rounded(sum(_money(r.creator_earnings) for r in rows))
            ),
            "total_platform_fee": float(_rounded(sum(_money(r.platform_fee) for r in rows))),
            "by_type": by_type,
            "stats": _stats_out(stats_row) if stats_row is not None else None,
        }

    async def user_stats(self, db: AsyncSession, user_id: int) -> dict:
        row = await user_revenue_stats_crud.get_by(db, user_id=user_id)
        if row is None:
            # 与 v2 一致：没有统计行时返回一份全 0 的空快照，而不是 404
            return {
                "user_id": user_id,
                "total_earnings": 0.0,
                "total_paid": 0.0,
                "pending_earnings": 0.0,
                "available_balance": 0.0,
                "last_payout_at": None,
            }
        return _stats_out(row)

    async def platform_stats(
        self, db: AsyncSession, *, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> dict:
        """平台维度统计：收益聚合 + 提现聚合（均为 SQL 聚合）"""
        conditions = []
        if start_date is not None:
            conditions.append(RevenueRecord.created_at >= start_date)
        if end_date is not None:
            conditions.append(RevenueRecord.created_at <= end_date)

        totals = (
            await db.execute(
                select(
                    func.count().label("count"),
                    func.coalesce(func.sum(RevenueRecord.amount), 0).label("amount"),
                    func.coalesce(func.sum(RevenueRecord.platform_fee), 0).label("platform_fee"),
                    func.coalesce(func.sum(RevenueRecord.creator_earnings), 0).label(
                        "creator_earnings"
                    ),
                ).where(*conditions)
            )
        ).one()

        type_rows = (
            await db.execute(
                select(
                    RevenueRecord.revenue_type,
                    func.count().label("count"),
                    func.coalesce(func.sum(RevenueRecord.amount), 0).label("amount"),
                )
                .where(*conditions)
                .group_by(RevenueRecord.revenue_type)
            )
        ).all()

        payout_rows = (
            await db.execute(
                select(
                    PayoutRequest.status,
                    func.count().label("count"),
                    func.coalesce(func.sum(PayoutRequest.amount), 0).label("amount"),
                ).group_by(PayoutRequest.status)
            )
        ).all()
        payouts = {
            str(row.status): {
                "count": int(row.count or 0),
                "amount": float(_rounded(_money(row.amount))),
            }
            for row in payout_rows
        }
        payouts.setdefault("pending", {"count": 0, "amount": 0.0})
        payouts.setdefault("approved", {"count": 0, "amount": 0.0})
        payouts.setdefault("completed", {"count": 0, "amount": 0.0})
        payouts.setdefault("rejected", {"count": 0, "amount": 0.0})

        return {
            "total_revenue": float(_rounded(_money(totals.amount))),
            "total_platform_fee": float(_rounded(_money(totals.platform_fee))),
            "total_creator_earnings": float(_rounded(_money(totals.creator_earnings))),
            "record_count": int(totals.count or 0),
            "total_payouts": payouts["completed"]["amount"],
            "pending_payouts": payouts["pending"]["amount"],
            "by_type": [
                {
                    "revenue_type": row.revenue_type,
                    "count": int(row.count or 0),
                    "amount": float(_rounded(_money(row.amount))),
                }
                for row in type_rows
            ],
            "payouts": payouts,
        }


revenue_record_service = RevenueRecordService()


class PayoutService:
    """提现申请与审批"""

    async def _min_payout_amount(self, db: AsyncSession) -> Decimal:
        """最低提现额度：取 advertisement 类型的配置，缺省 100（与 v2 同口径）"""
        config = await revenue_sharing_config_crud.get_by(db, revenue_type="advertisement")
        if config is not None and config.min_payout_amount is not None:
            return _money(config.min_payout_amount)
        return DEFAULT_MIN_PAYOUT

    async def list_payouts(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await payout_request_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"user_id": user_id, "status": status},
        )
        return [_payout_out(r) for r in rows], total

    async def create_payout(self, db: AsyncSession, payload: PayoutRequestCreate) -> dict:
        amount = _rounded(_money(payload.amount))
        min_amount = await self._min_payout_amount(db)
        if amount < min_amount:
            raise BadRequestError(f"提现金额不能低于最低额度 {min_amount}")
        stats = await user_stats_service.get_or_create(db, payload.user_id)
        if _money(stats.available_balance) < amount:
            raise BadRequestError("可用余额不足")
        now = datetime.now()
        row = await payout_request_crud.create(
            db,
            payload.model_dump(exclude={"amount"})
            | {"amount": amount, "status": "pending", "created_at": now, "updated_at": now},
        )
        # 冻结：立即从可用余额扣减（驳回时退还）
        await user_revenue_stats_crud.update(
            db,
            stats,
            {
                "available_balance": _rounded(_money(stats.available_balance) - amount),
                "updated_at": now,
            },
        )
        return _payout_out(row)

    async def _decide(
        self,
        db: AsyncSession,
        payout_id: int,
        *,
        admin_id: int,
        notes: Optional[str],
        status: str,
        allowed_from: tuple[str, ...],
    ) -> dict:
        row = await payout_request_crud.get(db, payout_id)
        if row is None:
            raise NotFoundError("提现申请不存在")
        if row.status not in allowed_from:
            raise BadRequestError(
                f"当前状态 {row.status} 不能执行该操作（允许的来源状态：{'/'.join(allowed_from)}）"
            )
        updated = await payout_request_crud.update(
            db,
            row,
            {
                "status": status,
                "processed_by": admin_id,
                "processed_at": datetime.now(),
                "admin_notes": notes,
                "updated_at": datetime.now(),
            },
        )
        return _payout_out(updated)

    async def approve(
        self, db: AsyncSession, payout_id: int, *, admin_id: int, notes: Optional[str] = None
    ) -> dict:
        result = await self._decide(
            db, payout_id, admin_id=admin_id, notes=notes, status="approved", allowed_from=("pending",)
        )
        # 通过：已支付累加、待结算扣减（与 v2 一致）
        amount = _money(result.get("amount"))
        await user_stats_service.apply_delta(
            db,
            int(result["user_id"]),
            total_paid=amount,
            pending_earnings=-amount,
        )
        return result

    async def complete(
        self, db: AsyncSession, payout_id: int, *, admin_id: int, notes: Optional[str] = None
    ) -> dict:
        """完成打款：**只能从 approved 进入**（真实打款通道属二期，这里只做状态流转）"""
        return await self._decide(
            db,
            payout_id,
            admin_id=admin_id,
            notes=notes,
            status="completed",
            allowed_from=("approved",),
        )

    async def reject(
        self, db: AsyncSession, payout_id: int, *, admin_id: int, notes: Optional[str] = None
    ) -> dict:
        result = await self._decide(
            db, payout_id, admin_id=admin_id, notes=notes, status="rejected", allowed_from=("pending",)
        )
        # 驳回：退还冻结的余额
        await user_stats_service.apply_delta(
            db, int(result["user_id"]), available_balance=_money(result.get("amount"))
        )
        return result


payout_service = PayoutService()


class SharingConfigService:
    """收益分成配置"""

    async def list_configs(self, db: AsyncSession) -> list[dict]:
        """按 ``REVENUE_TYPES`` 逐个取配置，只返回已存在的项（与 v2 一致）"""
        result: list[dict] = []
        for revenue_type in REVENUE_TYPES:
            row = await revenue_sharing_config_crud.get_by(db, revenue_type=revenue_type)
            if row is not None:
                result.append(_config_out(row))
        return result

    async def update_config(
        self, db: AsyncSession, revenue_type: str, payload: SharingConfigUpdate
    ) -> dict:
        _assert_revenue_type(revenue_type)
        row = await revenue_sharing_config_crud.get_by(db, revenue_type=revenue_type)
        if row is None:
            raise NotFoundError("分成配置不存在（该收益类型尚未建立配置）")
        data = payload.model_dump(exclude_unset=True)
        if not data:
            return _config_out(row)
        updated = await revenue_sharing_config_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _config_out(updated)


sharing_config_service = SharingConfigService()
