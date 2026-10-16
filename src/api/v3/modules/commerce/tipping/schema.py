"""tipping 模块的请求 / 响应模型

**金额单位统一为「分」**（与支付插件一致），对外展示时另给 ``*_yuan`` 便于前端直接显示。

打赏链路（复用批次 7）：``POST /tip`` → 写 ``tips``（pending）→ 调 payment-gateway 插件下单；
网关回调 → ``POST /callback/{provider}`` → 插件**验签** → 命中 ``order_no`` 才置为 ``paid``。
**没有验签通过的回调就永远停在 pending**（不可能"假装已付"）。

提现走**人工打款**：状态流转 ``pending → approved / rejected → paid``。
理由见 ``shared/models/tipping/tip_withdrawal.py`` 的说明（插件只有收款能力，没有代付）。
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: 打赏状态
TIP_STATUSES: tuple[str, ...] = ("pending", "paid", "failed", "refunded")
#: 支付网关判定"成功"的状态（与 commerce/payment 的 SUCCESS_STATUSES 保持一致）
GATEWAY_SUCCESS_STATUSES: tuple[str, ...] = ("succeeded", "completed", "paid")
#: 提现状态
WITHDRAWAL_STATUSES: tuple[str, ...] = ("pending", "approved", "rejected", "paid")

#: 单笔打赏范围（分）：1 元 ~ 1000 元
MIN_TIP_CENTS = 100
MAX_TIP_CENTS = 100_000
#: 预设金额（分）
TIP_PRESETS: tuple[int, ...] = (500, 1000, 2000, 5000, 10000, 20000)
#: 最低提现额（分）：10 元
MIN_WITHDRAW_CENTS = 1000
#: 提现手续费率（6%，显式化 —— v2 完全没有手续费与到账额概念）
WITHDRAW_FEE_RATE = 0.06
#: 支持的提现方式
WITHDRAW_METHODS: tuple[str, ...] = ("alipay", "wechat", "bank")


class TipConfigOut(SchemaBase):
    min_amount: int
    max_amount: int
    presets: list[int]
    min_withdraw: int
    withdraw_fee_rate: float
    withdraw_methods: list[str]


class TipCreateRequest(SchemaBase):
    author_id: int
    amount: int = Field(ge=MIN_TIP_CENTS, le=MAX_TIP_CENTS, description="打赏金额（分）")
    article_id: Optional[int] = None
    message: Optional[str] = Field(default=None, max_length=255)
    provider: Optional[str] = Field(default=None, max_length=32)
    return_url: Optional[str] = Field(default=None, max_length=500)
    cancel_url: Optional[str] = Field(default=None, max_length=500)
    notify_url: Optional[str] = Field(default=None, max_length=500)


class TipOut(SchemaBase):
    id: int
    user_id: int
    username: Optional[str] = None
    author_id: int
    author_name: Optional[str] = None
    article_id: Optional[int] = None
    amount: int
    amount_yuan: float
    message: Optional[str] = None
    status: str
    order_no: Optional[str] = None
    provider: Optional[str] = None
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class TipCreateResult(SchemaBase):
    tip: TipOut
    payment: dict = Field(default_factory=dict, description="支付插件返回的调起参数")


class TipRankingItem(SchemaBase):
    rank: int
    author_id: int
    username: Optional[str] = None
    total: int = Field(description="累计收到（分）")
    count: int = Field(description="打赏笔数")


class EarningsOut(SchemaBase):
    """打赏收益概要（**分**）

    ``available`` = 已结算收益 - 已提现（含待审与已批准未打款的部分），不会算成负数。
    """

    total_received: int = 0
    settled: int = 0
    pending: int = 0
    withdrawn: int = 0
    available: int = 0


class WithdrawCreateRequest(SchemaBase):
    amount: int = Field(ge=MIN_WITHDRAW_CENTS, description="提现金额（分）")
    method: str = Field(min_length=1, max_length=32)
    account: str = Field(min_length=1, max_length=255)
    account_name: str = Field(min_length=1, max_length=100)


class WithdrawalOut(SchemaBase):
    id: int
    user_id: int
    username: Optional[str] = None
    amount: int
    fee: int = 0
    actual_amount: int = 0
    method: Optional[str] = None
    account_name: Optional[str] = None
    status: str
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    paid_at: Optional[datetime] = None
    transaction_id: Optional[str] = None
    created_at: Optional[datetime] = None


class WithdrawalReviewRequest(SchemaBase):
    approve: bool
    comment: Optional[str] = Field(default=None, max_length=500)


class WithdrawalPaidRequest(SchemaBase):
    transaction_id: str = Field(min_length=1, max_length=128, description="打款流水号")
    comment: Optional[str] = Field(default=None, max_length=500)


class TipStatsOut(SchemaBase):
    tip_count: int = 0
    paid_count: int = 0
    total_amount: int = 0
    paid_amount: int = 0
    withdrawal_count: int = 0
    withdrawal_pending: int = 0
    withdrawal_paid: int = 0
    top_authors: list[TipRankingItem] = Field(default_factory=list)
