"""mobile/vip 的请求 / 响应模型（前台 VIP 自助）

金额单位是**元**（与 ``vip_plans.price`` 的 ``NUMERIC(10, 2)`` 一致），不是 commerce 域的"分"。

订阅状态与 ``marketing/vip``、``shared.services.core.membership.MembershipService``
以及前端展示统一为 **0=进行中 / 1=已过期 / 2=已取消**。
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

# ---- 订阅状态（权威语义，见 MembershipService 的常量注释）----
SUB_ACTIVE, SUB_EXPIRED, SUB_CANCELLED = 0, 1, 2

# ---- 支付订单状态 ----
ORDER_PENDING, ORDER_PAID, ORDER_FAILED = "pending", "paid", "failed"

#: 支付网关判定"成功"的状态（与 commerce/payment、commerce/tipping 保持一致）
GATEWAY_SUCCESS_STATUSES: tuple[str, ...] = ("succeeded", "completed", "paid")
#: 判定"失败"的状态
GATEWAY_FAILED_STATUSES: tuple[str, ...] = ("failed", "cancelled", "canceled", "error")


class VipStatusOut(SchemaBase):
    """我的 VIP 状态"""

    is_vip: bool = False
    level: int = 0
    plan_name: Optional[str] = None
    subscription_id: Optional[int] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    #: 剩余天数（未开通或已过期时为 0）
    days_left: int = 0


class VipSubscriptionItem(SchemaBase):
    """订阅记录（含历史）"""

    id: int
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    level: Optional[int] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: int = SUB_ACTIVE
    payment_amount: Optional[float] = None
    transaction_id: Optional[str] = None
    created_at: Optional[datetime] = None


class VipOrderItem(SchemaBase):
    """支付订单（待支付 / 已支付 / 失败）"""

    id: int
    order_no: str
    plan_id: int
    plan_name: Optional[str] = None
    amount: float = 0
    status: str = ORDER_PENDING
    provider: Optional[str] = None
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MyVipOut(SchemaBase):
    status: VipStatusOut
    subscriptions: list[VipSubscriptionItem] = Field(default_factory=list)
    pending_orders: list[VipOrderItem] = Field(default_factory=list)


class CreatePaymentRequest(SchemaBase):
    """开通 / 续费下单（金额由服务端按套餐取，**不接受外部传入**）"""

    plan_id: int
    provider: Optional[str] = Field(default=None, max_length=32)
    return_url: Optional[str] = Field(default=None, max_length=500)
    cancel_url: Optional[str] = Field(default=None, max_length=500)
    notify_url: Optional[str] = Field(default=None, max_length=500)


class CreatePaymentResult(SchemaBase):
    order: VipOrderItem
    payment: dict = Field(default_factory=dict, description="支付插件返回的调起参数")


class CancelSubscriptionRequest(SchemaBase):
    comment: Optional[str] = Field(default=None, max_length=500)


class AccessCheckOut(SchemaBase):
    """内容访问判定结果"""

    has_access: bool
    reason: Optional[str] = None
    article_id: Optional[int] = None
    required_level: int = 0
    current_level: int = 0
    is_vip: bool = False


class PremiumContentItem(SchemaBase):
    """付费内容条目（`accessible` 为当前用户的真实可读性）"""

    id: int
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    cover_image: Optional[str] = None
    views: int = 0
    likes: int = 0
    required_vip_level: int = 0
    accessible: bool = False
    user_id: Optional[int] = None
    category_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
