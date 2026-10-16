"""revenue 模块的请求 / 响应模型

金额列均为 ``Numeric(10, 2)``，出参统一按 ``float`` 暴露。

``revenue_type`` 在库中是 ``String(50)``（不是数据库枚举），合法值由
``service.REVENUE_TYPES`` 做白名单校验 —— 校验放在服务层是为了让
「分成配置」和「收益记录」共用同一份取值定义。
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


# ---------------------------------------------------------------- 收益记录
class RevenueRecordCreate(SchemaBase):
    user_id: int = Field(description="创作者用户 ID")
    revenue_type: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0, description="收益金额")
    description: Optional[str] = None
    reference_id: Optional[int] = Field(default=None, description="关联记录 ID（广告 / 订单等）")
    reference_type: Optional[str] = Field(default=None, max_length=50)


class RevenueRecordOut(SchemaBase):
    id: int
    user_id: Optional[int] = None
    revenue_type: Optional[str] = None
    amount: Optional[float] = None
    platform_fee: Optional[float] = None
    creator_earnings: Optional[float] = None
    description: Optional[str] = None
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 提现申请
class PayoutRequestCreate(SchemaBase):
    user_id: int = Field(description="提现用户 ID（用户端接口固定为登录用户）")
    amount: float = Field(gt=0, description="提现金额")
    payment_method: str = Field(min_length=1, max_length=50, description="alipay / wechat / bank_transfer")
    payment_account: str = Field(min_length=1, max_length=200)
    account_name: Optional[str] = Field(default=None, max_length=100)


class PayoutDecision(SchemaBase):
    """通过 / 完成 / 驳回的统一入参"""

    notes: Optional[str] = Field(default=None, description="管理员备注")


class PayoutRequestOut(SchemaBase):
    id: int
    user_id: Optional[int] = None
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    payment_account: Optional[str] = None
    account_name: Optional[str] = None
    status: Optional[str] = None
    admin_notes: Optional[str] = None
    processed_by: Optional[int] = None
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 分成配置
class SharingConfigUpdate(SchemaBase):
    platform_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    creator_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    min_payout_amount: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SharingConfigOut(SchemaBase):
    id: int
    revenue_type: Optional[str] = None
    platform_percentage: Optional[float] = None
    creator_percentage: Optional[float] = None
    min_payout_amount: Optional[float] = None
    is_active: bool = True
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 用户收益统计
class UserRevenueStatsOut(SchemaBase):
    id: int
    user_id: Optional[int] = None
    total_earnings: Optional[float] = None
    total_paid: Optional[float] = None
    pending_earnings: Optional[float] = None
    available_balance: Optional[float] = None
    last_payout_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
