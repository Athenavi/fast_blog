"""tipping 模块业务逻辑（打赏 / 提现）

**与 v2 的差异**（v2 在 `services/advanced_features/tipping_system.py`）：

| v2 的做法 | 问题 | 本模块 |
|---|---|---|
| 进程内内存单例 | 重启即失、多 worker 各一份 | 真表 ``tips`` / ``tip_withdrawals`` |
| 查询用了**不存在的列** ``Article.user_id`` | 真列名是 ``user``，一次查询都跑不通 | 用真实列名 |
| 打赏只是往字典里塞一条 | "打赏成功"不涉及任何真实支付 | **接批次 7 的 payment-gateway 插件**：下单 → 网关回调 → **插件验签通过**才置 ``paid`` |
| 提现无余额校验、无手续费 | 想提多少提多少 | 余额 = 已结算打赏 − 已申请提现；显式手续费率与到账额 |
| 提现"完成"只是改个状态 | 没有打款凭据 | ``approved → paid`` 必须带**打款流水号**（人工转账后登记） |

**不做自动打款**：插件层只有收款能力（``execute:custom:payment``），没有代付/转账产品。
所以提现这一环如实走人工，但状态、金额、手续费、到账额、流水号全部入库，可对账。
"""

import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.tipping import Tip, TipWithdrawal
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.commerce.payment.schema import PaymentInitiateRequest
from src.api.v3.modules.commerce.payment.service import payment_flow_service
from src.api.v3.modules.commerce.tipping.crud import tip_crud, tip_withdrawal_crud
from src.api.v3.modules.commerce.tipping.schema import (
    GATEWAY_SUCCESS_STATUSES,
    MAX_TIP_CENTS,
    MIN_TIP_CENTS,
    MIN_WITHDRAW_CENTS,
    TIP_PRESETS,
    WITHDRAW_FEE_RATE,
    WITHDRAW_METHODS,
    EarningsOut,
    TipConfigOut,
    TipCreateRequest,
    TipOut,
    TipRankingItem,
    WithdrawCreateRequest,
    WithdrawalOut,
    WithdrawalPaidRequest,
    WithdrawalReviewRequest,
)

logger = get_logger("commerce.tipping")

#: 网关侧「失败」状态
GATEWAY_FAILED_STATUSES = ("failed", "cancelled", "canceled", "expired")
#: 占用余额的提现状态（待审 / 已批准 / 已打款都算已占用）
WITHDRAWAL_OCCUPYING = ("pending", "approved", "paid")
MAX_PAGE_SIZE = 100
MAX_RANKING = 100


def _yuan(cents: Optional[int]) -> float:
    return round(int(cents or 0) / 100, 2)


class TippingService:
    """打赏与提现"""

    # ------------------------------------------------------------ 配置
    @staticmethod
    def config() -> dict:
        return TipConfigOut(
            min_amount=MIN_TIP_CENTS,
            max_amount=MAX_TIP_CENTS,
            presets=list(TIP_PRESETS),
            min_withdraw=MIN_WITHDRAW_CENTS,
            withdraw_fee_rate=WITHDRAW_FEE_RATE,
            withdraw_methods=list(WITHDRAW_METHODS),
        ).model_dump()

    # ------------------------------------------------------------ 拼装
    async def _names(self, db: AsyncSession, user_ids: list[int]) -> dict[int, str]:
        ids = {int(i) for i in user_ids if i is not None}
        if not ids:
            return {}
        rows = (await db.execute(select(User.id, User.username).where(User.id.in_(ids)))).all()
        return {int(row.id): row.username for row in rows}

    async def _tip_out(
        self, db: AsyncSession, row: Tip, names: Optional[dict[int, str]] = None
    ) -> dict:
        mapping = names if names is not None else await self._names(db, [row.user_id, row.author_id])
        return TipOut(
            id=row.id,
            user_id=row.user_id,
            username=mapping.get(row.user_id),
            author_id=row.author_id,
            author_name=mapping.get(row.author_id),
            article_id=row.article_id,
            amount=int(row.amount or 0),
            amount_yuan=_yuan(row.amount),
            message=row.message,
            status=row.status or "pending",
            order_no=row.order_no,
            provider=row.provider,
            transaction_id=row.transaction_id,
            paid_at=row.paid_at,
            created_at=row.created_at,
        ).model_dump(mode="json")

    async def _withdrawal_out(
        self, db: AsyncSession, row: TipWithdrawal, names: Optional[dict[int, str]] = None
    ) -> dict:
        mapping = names if names is not None else await self._names(db, [row.user_id])
        return WithdrawalOut(
            id=row.id,
            user_id=row.user_id,
            username=mapping.get(row.user_id),
            amount=int(row.amount or 0),
            fee=int(row.fee or 0),
            actual_amount=int(row.actual_amount or 0),
            method=row.method,
            account_name=row.account_name,
            status=row.status or "pending",
            reviewed_at=row.reviewed_at,
            review_comment=row.review_comment,
            paid_at=row.paid_at,
            transaction_id=row.transaction_id,
            created_at=row.created_at,
        ).model_dump(mode="json")

    # ------------------------------------------------------------ 打赏
    async def create(self, db: AsyncSession, user_id: int, payload: TipCreateRequest) -> dict:
        """发起打赏：先落 pending，再去支付插件下单（**下单失败就把这条置为 failed**）"""
        if payload.author_id == user_id:
            raise BadRequestError("不能给自己打赏")
        if await db.get(User, payload.author_id) is None:
            raise NotFoundError("被打赏的用户不存在")
        if payload.article_id is not None and await db.get(Article, payload.article_id) is None:
            raise NotFoundError("文章不存在")

        now = datetime.now()
        order_no = f"TIP{now:%Y%m%d%H%M%S}{secrets.token_hex(4).upper()}"
        tip = await tip_crud.create(
            db,
            {
                "user_id": user_id,
                "author_id": payload.author_id,
                "article_id": payload.article_id,
                "amount": int(payload.amount),
                "message": payload.message,
                "status": "pending",
                "order_no": order_no,
                "provider": payload.provider,
                "created_at": now,
                "updated_at": now,
            },
        )
        subject = f"打赏 {_yuan(payload.amount)} 元"
        try:
            payment = await payment_flow_service.initiate(
                db,
                PaymentInitiateRequest(
                    order_id=order_no,
                    amount=_yuan(payload.amount),
                    subject=subject,
                    return_url=payload.return_url,
                    cancel_url=payload.cancel_url,
                    notify_url=payload.notify_url,
                ),
                user_id,
            )
        except Exception:
            await tip_crud.update(db, tip, {"status": "failed", "updated_at": datetime.now()})
            raise

        if isinstance(payment, dict) and payment.get("success") is False:
            await tip_crud.update(db, tip, {"status": "failed", "updated_at": datetime.now()})
            raise BadRequestError(f"发起支付失败：{payment.get('error') or '支付插件返回失败'}")

        logger.info("发起打赏: user=%s author=%s amount=%s order=%s", user_id, payload.author_id, tip.amount, order_no)
        return {"tip": await self._tip_out(db, tip), "payment": payment or {}}

    async def handle_callback(
        self, db: AsyncSession, *, provider: str, payload: dict, headers: Optional[dict] = None
    ) -> dict:
        """网关回调：复用 ``PaymentFlowService`` 的**验签**，通过后再同步打赏状态

        注意：打赏订单**不写** ``payment_transactions``（那是财务模块的表），
        所以这里靠回调里的 ``order_id``（= 本地 ``order_no``）直接找到 ``tips``。
        """
        result = await payment_flow_service.handle_callback(
            db, provider=provider, payload=payload, headers=headers
        )
        if not result.get("verified"):
            return {"verified": False, "provider": provider}

        order_no = result.get("order_id")
        gateway_status = str(result.get("status") or "succeeded")
        tip = await tip_crud.get_by(db, order_no=order_no) if order_no else None
        if tip is None:
            logger.warning("打赏回调找不到订单: provider=%s order_no=%s", provider, order_no)
            return result | {"tip_updated": False}

        now = datetime.now()
        if gateway_status in GATEWAY_SUCCESS_STATUSES:
            if tip.status != "paid":
                tip = await tip_crud.update(
                    db,
                    tip,
                    {
                        "status": "paid",
                        "paid_at": now,
                        "provider": provider,
                        "transaction_id": result.get("transaction_id"),
                        "updated_at": now,
                    },
                )
        elif gateway_status in GATEWAY_FAILED_STATUSES:
            tip = await tip_crud.update(db, tip, {"status": "failed", "updated_at": now})
        return result | {"tip_updated": True, "tip_status": tip.status, "order_no": order_no}

    async def my_tips(
        self, db: AsyncSession, user_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        rows, total = await tip_crud.list(
            db, page=page, page_size=min(page_size, MAX_PAGE_SIZE), filters={"user_id": user_id}
        )
        names = await self._names(db, [row.author_id for row in rows] + [user_id])
        return [await self._tip_out(db, row, names) for row in rows], total

    async def received(
        self, db: AsyncSession, user_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        rows, total = await tip_crud.list(
            db, page=page, page_size=min(page_size, MAX_PAGE_SIZE), filters={"author_id": user_id}
        )
        names = await self._names(db, [row.user_id for row in rows] + [user_id])
        return [await self._tip_out(db, row, names) for row in rows], total

    async def article_tips(
        self, db: AsyncSession, article_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        rows, total = await tip_crud.list(
            db,
            page=page,
            page_size=min(page_size, MAX_PAGE_SIZE),
            filters={"article_id": article_id, "status": "paid"},
        )
        names = await self._names(db, [row.user_id for row in rows] + [row.author_id for row in rows])
        return [await self._tip_out(db, row, names) for row in rows], total

    async def _sum(self, db: AsyncSession, *conditions) -> int:
        stmt = select(func.coalesce(func.sum(Tip.amount), 0)).select_from(Tip)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await db.execute(stmt)).scalar() or 0)

    async def earnings(self, db: AsyncSession, user_id: int) -> dict:
        """收益概要（分）—— ``available`` 才是可提现额"""
        settled = await self._sum(db, Tip.author_id == user_id, Tip.status == "paid")
        pending = await self._sum(db, Tip.author_id == user_id, Tip.status == "pending")
        withdrawn = int(
            (
                await db.execute(
                    select(func.coalesce(func.sum(TipWithdrawal.amount), 0)).where(
                        TipWithdrawal.user_id == user_id,
                        TipWithdrawal.status.in_(WITHDRAWAL_OCCUPYING),
                    )
                )
            ).scalar()
            or 0
        )
        available = max(0, settled - withdrawn)
        return EarningsOut(
            total_received=settled + pending,
            settled=settled,
            pending=pending,
            withdrawn=withdrawn,
            available=available,
        ).model_dump()

    async def ranking(self, db: AsyncSession, *, limit: int = 20) -> list[dict]:
        rows = (
            await db.execute(
                select(
                    Tip.author_id,
                    func.coalesce(func.sum(Tip.amount), 0).label("total"),
                    func.count(Tip.id).label("count"),
                )
                .where(Tip.status == "paid")
                .group_by(Tip.author_id)
                .order_by(func.sum(Tip.amount).desc())
                .limit(max(1, min(limit, MAX_RANKING)))
            )
        ).all()
        names = await self._names(db, [row.author_id for row in rows])
        return [
            TipRankingItem(
                rank=index + 1,
                author_id=row.author_id,
                username=names.get(row.author_id),
                total=int(row.total or 0),
                count=int(row.count or 0),
            ).model_dump()
            for index, row in enumerate(rows)
        ]

    async def stats(self, db: AsyncSession) -> dict:
        counts = (
            await db.execute(select(Tip.status, func.count(Tip.id)).group_by(Tip.status))
        ).all()
        by_status = {str(status): int(count or 0) for status, count in counts}
        tip_count = sum(by_status.values())
        paid_count = by_status.get("paid", 0)

        total_amount = await self._sum(db)
        paid_amount = await self._sum(db, Tip.status == "paid")

        withdrawal_rows = (
            await db.execute(
                select(TipWithdrawal.status, func.count(TipWithdrawal.id)).group_by(
                    TipWithdrawal.status
                )
            )
        ).all()
        withdrawals = {str(status): int(count or 0) for status, count in withdrawal_rows}
        return {
            "tip_count": tip_count,
            "paid_count": paid_count,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "withdrawal_count": sum(withdrawals.values()),
            "withdrawal_pending": withdrawals.get("pending", 0),
            "withdrawal_paid": withdrawals.get("paid", 0),
            "top_authors": await self.ranking(db, limit=10),
        }

    # ------------------------------------------------------------ 提现
    async def withdraw(self, db: AsyncSession, user_id: int, payload: WithdrawCreateRequest) -> dict:
        if payload.method not in WITHDRAW_METHODS:
            raise BadRequestError(f"不支持的提现方式：{payload.method}（可选 {', '.join(WITHDRAW_METHODS)}）")
        earnings = await self.earnings(db, user_id)
        available = int(earnings["available"])
        if payload.amount > available:
            raise BadRequestError(f"可提现余额不足（当前 {_yuan(available)} 元，申请 {_yuan(payload.amount)} 元）")

        fee = int(round(payload.amount * WITHDRAW_FEE_RATE))
        now = datetime.now()
        row = await tip_withdrawal_crud.create(
            db,
            {
                "user_id": user_id,
                "amount": int(payload.amount),
                "fee": fee,
                "actual_amount": int(payload.amount) - fee,
                "method": payload.method,
                "account": payload.account,
                "account_name": payload.account_name,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            },
        )
        logger.info("提现申请: user=%s amount=%s", user_id, payload.amount)
        return await self._withdrawal_out(db, row)

    async def my_withdrawals(
        self, db: AsyncSession, user_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        rows, total = await tip_withdrawal_crud.list(
            db, page=page, page_size=min(page_size, MAX_PAGE_SIZE), filters={"user_id": user_id}
        )
        return [await self._withdrawal_out(db, row) for row in rows], total

    async def withdrawals(
        self,
        db: AsyncSession,
        *,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        filters = {"status": status} if status else None
        rows, total = await tip_withdrawal_crud.list(
            db, page=page, page_size=min(page_size, MAX_PAGE_SIZE), filters=filters
        )
        names = await self._names(db, [row.user_id for row in rows])
        return [await self._withdrawal_out(db, row, names) for row in rows], total

    async def review_withdrawal(
        self,
        db: AsyncSession,
        withdrawal_id: int,
        payload: WithdrawalReviewRequest,
        operator_id: int,
    ) -> dict:
        row = await tip_withdrawal_crud.get(db, withdrawal_id)
        if row is None:
            raise NotFoundError("提现申请不存在")
        if row.status != "pending":
            raise BadRequestError(f"当前状态（{row.status}）不可审核，只有待审申请能审核")
        now = datetime.now()
        row = await tip_withdrawal_crud.update(
            db,
            row,
            {
                "status": "approved" if payload.approve else "rejected",
                "reviewed_at": now,
                "reviewer_id": operator_id,
                "review_comment": payload.comment,
                "updated_at": now,
            },
        )
        logger.info("提现审核: id=%s approve=%s operator=%s", withdrawal_id, payload.approve, operator_id)
        return await self._withdrawal_out(db, row)

    async def mark_paid(
        self,
        db: AsyncSession,
        withdrawal_id: int,
        payload: WithdrawalPaidRequest,
        operator_id: int,
    ) -> dict:
        """标记已打款 —— **必须提供流水号**（人工转账的凭据），不接受"无凭据已完成" """
        row = await tip_withdrawal_crud.get(db, withdrawal_id)
        if row is None:
            raise NotFoundError("提现申请不存在")
        if row.status != "approved":
            raise BadRequestError(f"当前状态（{row.status}）不可打款，只有已批准的申请能标记打款")
        now = datetime.now()
        row = await tip_withdrawal_crud.update(
            db,
            row,
            {
                "status": "paid",
                "paid_at": now,
                "transaction_id": payload.transaction_id,
                "review_comment": payload.comment or row.review_comment,
                "updated_at": now,
            },
        )
        logger.info(
            "提现打款: id=%s txn=%s operator=%s", withdrawal_id, payload.transaction_id, operator_id
        )
        return await self._withdrawal_out(db, row)


tipping_service = TippingService()
