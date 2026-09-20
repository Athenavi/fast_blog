"""mobile/vip 的业务逻辑（前台 VIP 自助：开通 / 订阅 / 内容访问）

**复用** ``shared.services.core.membership.MembershipService``：状态查询、内容访问判定、
开通与取消订阅都不重写；本模块只做两件事：

1. 把 Service 的返回整理成前台要的形状（并补上"待支付订单"）；
2. 接上**真实支付链路**（批次 7 的 payment-gateway 插件 + 验签回调）：
   ``create-payment`` 先落 ``vip_payment_orders``（pending）再去插件下单，
   回调经 ``PaymentFlowService`` **验签通过**后才调 ``create_subscription`` 真正开通。
   **没有验签通过的回调就永远停在 pending**（不存在"假装已开通"的路径）。

订阅状态语义统一为 **0=进行中 / 1=已过期 / 2=已取消**（见 ``MembershipService`` 的常量注释）。
"""

import secrets
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.vip import VIPPlan, VIPSubscription
from shared.services.core.membership import create_membership_service
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.commerce.payment.schema import PaymentInitiateRequest
from src.api.v3.modules.commerce.payment.service import payment_flow_service
from src.api.v3.modules.mobile.vip.crud import vip_payment_order_crud
from src.api.v3.modules.mobile.vip.schema import (
    GATEWAY_FAILED_STATUSES,
    GATEWAY_SUCCESS_STATUSES,
    ORDER_FAILED,
    ORDER_PAID,
    ORDER_PENDING,
    AccessCheckOut,
    CancelSubscriptionRequest,
    CreatePaymentRequest,
    MyVipOut,
    VipOrderItem,
    VipStatusOut,
    VipSubscriptionItem,
)

logger = get_logger("mobile.vip")

#: 我的订阅页最多带出的待支付订单数
MAX_PENDING_ORDERS = 20


def _parse_dt(value: Any) -> Optional[datetime]:
    """``MembershipService`` 返回的是 isoformat 字符串，这里统一转成 datetime"""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _days_left(expires_at: Optional[datetime]) -> int:
    if expires_at is None:
        return 0
    return max((expires_at - datetime.now()).days, 0)


class MobileVipService:
    """前台 VIP 自助（全部以当前用户为界）"""

    # ------------------------------------------------------------ 我的订阅
    async def my_subscription(self, db: AsyncSession, user_id: int) -> dict:
        membership = create_membership_service(db)
        raw = await membership.get_user_vip_status(user_id)
        expires_at = _parse_dt(raw.get("expires_at"))

        status = VipStatusOut(
            is_vip=bool(raw.get("is_vip")),
            level=int(raw.get("level") or 0),
            plan_name=raw.get("plan_name"),
            subscription_id=raw.get("subscription_id"),
            expires_at=expires_at,
            days_left=_days_left(expires_at) if raw.get("is_vip") else 0,
        )

        rows = await membership.get_user_subscriptions(user_id)
        subscriptions = [VipSubscriptionItem(**row) for row in rows]
        # 当前生效的那条的 starts_at 不在 get_user_vip_status 里，从历史里补齐
        current = next((item for item in subscriptions if item.id == status.subscription_id), None)
        if current is not None:
            status.starts_at = current.starts_at

        return MyVipOut(
            status=status,
            subscriptions=subscriptions,
            pending_orders=await self._pending_orders(db, user_id),
        ).model_dump(mode="json")

    async def _pending_orders(self, db: AsyncSession, user_id: int) -> list[VipOrderItem]:
        rows, _total = await vip_payment_order_crud.list(
            db,
            page=1,
            page_size=MAX_PENDING_ORDERS,
            filters={"user_id": user_id, "status": ORDER_PENDING},
            order_by="created_at",
            order="desc",
        )
        return [await self._order_out(db, row) for row in rows]

    async def _order_out(self, db: AsyncSession, row) -> VipOrderItem:
        plan = await db.get(VIPPlan, row.plan_id)
        return VipOrderItem(
            id=row.id,
            order_no=row.order_no,
            plan_id=row.plan_id,
            plan_name=plan.name if plan is not None else None,
            amount=float(row.amount or 0),
            status=row.status or ORDER_PENDING,
            provider=row.provider,
            transaction_id=row.transaction_id,
            paid_at=row.paid_at,
            created_at=row.created_at,
        )

    # ------------------------------------------------------------ 下单
    async def create_payment(
        self, db: AsyncSession, user_id: int, payload: CreatePaymentRequest
    ) -> dict:
        """开通 / 续费下单：先落 pending 订单，再去支付插件下单

        金额**只按套餐价格取**（请求体里没有金额字段），下单失败（插件不可用 / 未配置渠道）
        就把这条订单置为 ``failed`` 并原样报错——不会"记一笔待发放"了事。
        """
        plan = await db.get(VIPPlan, payload.plan_id)
        if plan is None:
            raise NotFoundError("套餐不存在")
        if not plan.is_active:
            raise BadRequestError("套餐已停用，无法开通")
        price = float(plan.price or 0)
        if price <= 0:
            raise BadRequestError("该套餐价格无效（必须大于 0 元）")

        now = datetime.now()
        order_no = f"VIP{now:%Y%m%d%H%M%S}{secrets.token_hex(4).upper()}"
        order = await vip_payment_order_crud.create(
            db,
            {
                "user_id": user_id,
                "plan_id": plan.id,
                "amount": plan.price,
                "status": ORDER_PENDING,
                "order_no": order_no,
                "provider": payload.provider,
                "created_at": now,
                "updated_at": now,
            },
        )

        try:
            payment = await payment_flow_service.initiate(
                db,
                PaymentInitiateRequest(
                    order_id=order_no,
                    amount=price,
                    subject=f"VIP 会员：{plan.name or plan.id}",
                    return_url=payload.return_url,
                    cancel_url=payload.cancel_url,
                    notify_url=payload.notify_url,
                ),
                user_id,
            )
        except Exception:
            await vip_payment_order_crud.update(
                db, order, {"status": ORDER_FAILED, "updated_at": datetime.now()}
            )
            raise

        if isinstance(payment, dict) and payment.get("success") is False:
            await vip_payment_order_crud.update(
                db, order, {"status": ORDER_FAILED, "updated_at": datetime.now()}
            )
            raise BadRequestError(f"发起支付失败：{payment.get('error') or '支付插件返回失败'}")

        logger.info("VIP 下单: user=%s plan=%s amount=%s order=%s", user_id, plan.id, price, order_no)
        return {
            "order": (await self._order_out(db, order)).model_dump(mode="json"),
            "payment": payment or {},
        }

    # ------------------------------------------------------------ 网关回调
    async def handle_callback(
        self, db: AsyncSession, *, provider: str, payload: dict, headers: Optional[dict] = None
    ) -> dict:
        """网关回调：**验签通过**才把订单置为 paid 并开通订阅（重复投递幂等）"""
        result = await payment_flow_service.handle_callback(
            db, provider=provider, payload=payload, headers=headers
        )
        if not result.get("verified"):
            return {"verified": False, "provider": provider}

        order_no = result.get("order_id")
        gateway_status = str(result.get("status") or "succeeded")
        order = await vip_payment_order_crud.get_by(db, order_no=order_no) if order_no else None
        if order is None:
            logger.warning("VIP 回调找不到订单: provider=%s order_no=%s", provider, order_no)
            return result | {"order_updated": False, "subscribed": False}

        now = datetime.now()
        if gateway_status in GATEWAY_FAILED_STATUSES:
            order = await vip_payment_order_crud.update(
                db, order, {"status": ORDER_FAILED, "updated_at": now}
            )
            return result | {
                "order_updated": True,
                "order_status": order.status,
                "order_no": order_no,
                "subscribed": False,
            }
        if gateway_status not in GATEWAY_SUCCESS_STATUSES:
            # 既不是成功也不是失败（如 pending）：保持原状，等下一次回调
            return result | {
                "order_updated": False,
                "order_status": order.status,
                "order_no": order_no,
                "subscribed": False,
            }

        already_paid = order.status == ORDER_PAID
        if not already_paid:
            order = await vip_payment_order_crud.update(
                db,
                order,
                {
                    "status": ORDER_PAID,
                    "paid_at": now,
                    "provider": provider,
                    "transaction_id": result.get("transaction_id"),
                    "updated_at": now,
                },
            )

        subscribed = await self._activate(db, order)
        return result | {
            "order_updated": not already_paid,
            "order_status": order.status,
            "order_no": order_no,
            "subscribed": subscribed,
        }

    async def _activate(self, db: AsyncSession, order) -> bool:
        """按订单开通订阅（幂等：``transaction_id`` 命中同一订单号即视为已开通）"""
        existing = (
            await db.execute(
                select(VIPSubscription).where(VIPSubscription.transaction_id == order.order_no)
            )
        ).scalars().first()
        if existing is not None:
            return False

        membership = create_membership_service(db)
        outcome = await membership.create_subscription(
            order.user_id, order.plan_id, float(order.amount or 0), transaction_id=order.order_no
        )
        if not outcome.get("success"):
            logger.warning(
                "VIP 订阅开通失败: order=%s msg=%s", order.order_no, outcome.get("message")
            )
            return False
        logger.info(
            "VIP 订阅开通: user=%s plan=%s order=%s expires_at=%s",
            order.user_id,
            order.plan_id,
            order.order_no,
            outcome.get("expires_at"),
        )
        return True

    # ------------------------------------------------------------ 取消
    async def cancel_my_subscription(
        self, db: AsyncSession, user_id: int, payload: CancelSubscriptionRequest
    ) -> dict:
        """取消本人**当前生效**的订阅（没有生效订阅时 400）"""
        membership = create_membership_service(db)
        raw = await membership.get_user_vip_status(user_id)
        subscription_id = raw.get("subscription_id")
        if not raw.get("is_vip") or subscription_id is None:
            raise BadRequestError("当前没有生效中的订阅")

        outcome = await membership.cancel_subscription(int(subscription_id), user_id)
        if not outcome.get("success"):
            raise BadRequestError(outcome.get("message") or "取消订阅失败")
        if payload.comment:
            logger.info("取消订阅: user=%s sub=%s comment=%s", user_id, subscription_id, payload.comment)
        return {"success": True, "subscription_id": int(subscription_id)}

    # ------------------------------------------------------------ 内容访问
    async def check_access(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        article_id: Optional[int] = None,
        required_level: int = 0,
    ) -> dict:
        """内容访问判定：给了 ``article_id`` 就以文章自身的 VIP 设置为准"""
        required = max(int(required_level or 0), 0)
        if article_id is not None:
            article = await db.get(Article, article_id)
            if article is None:
                raise NotFoundError("文章不存在")
            required = max(int(article.required_vip_level or 0), 1) if article.is_vip_only else 0
            if article.is_vip_only and article.user == user_id:
                # 作者本人可读，但 `is_vip` 仍如实反映其真实等级（不是硬编码 True）
                membership = create_membership_service(db)
                current = int((await membership.get_user_vip_status(user_id)).get("level") or 0)
                return AccessCheckOut(
                    has_access=True,
                    reason="作者本人",
                    article_id=article_id,
                    required_level=required,
                    current_level=current,
                    is_vip=current > 0,
                ).model_dump(mode="json")

        membership = create_membership_service(db)
        verdict = await membership.check_content_access(user_id, int(article_id or 0), required)
        current_level = int((await membership.get_user_vip_status(user_id)).get("level") or 0)
        return AccessCheckOut(
            has_access=bool(verdict.get("has_access")),
            reason=verdict.get("reason"),
            article_id=article_id,
            required_level=required,
            current_level=current_level,
            is_vip=current_level > 0,
        ).model_dump(mode="json")

    async def premium_content(
        self, db: AsyncSession, user_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        """付费内容列表（每条带 ``accessible``：当前用户是否读得到）"""
        data = await create_membership_service(db).get_premium_content(
            user_id, page=page, page_size=page_size
        )
        items = data.get("articles") or []
        return items, int(data.get("total") or 0)


mobile_vip_service = MobileVipService()
