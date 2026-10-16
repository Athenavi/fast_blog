"""points 模块的请求 / 响应模型

兑拨相关约定：**兑拨规则**就是 ``points_rules`` 里 ``action`` 以 ``exchange:`` 开头的行
（``points`` 为负值即需要消耗的积分），因此不再单独建表。
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: 兑拨规则的 action 前缀
EXCHANGE_PREFIX = "exchange:"
#: 签到动作标识（与种子数据一致）
CHECKIN_ACTION = "daily_checkin"


class PointsAccountOut(SchemaBase):
    user_id: int
    balance: int = 0
    total_earned: int = 0
    total_spent: int = 0
    last_checkin_at: Optional[datetime] = Field(default=None, description="最后签到时间")
    checked_in_today: bool = Field(default=False, description="今天是否已签到")
    updated_at: Optional[datetime] = None


class PointsTransactionOut(SchemaBase):
    id: int
    user_id: Optional[int] = None
    amount: Optional[int] = None
    balance_after: Optional[int] = None
    action: Optional[str] = None
    description: Optional[str] = None
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    created_at: Optional[datetime] = None


class PointsRuleOut(SchemaBase):
    id: int
    action: Optional[str] = None
    points: Optional[int] = None
    description: Optional[str] = None
    daily_limit: int = 0
    is_active: bool = True
    sort_order: int = 0


class PointsRuleUpdate(SchemaBase):
    """只允许改这几个字段 —— ``action`` 是规则主键语义，创建后锁定"""

    points: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=255)
    daily_limit: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class LeaderboardItem(SchemaBase):
    rank: int
    user_id: int
    username: Optional[str] = None
    balance: int = 0


class ExchangeRuleOut(SchemaBase):
    """兑拨项：``cost`` 是需要消耗的**正数**积分"""

    action: str
    cost: int
    description: Optional[str] = None
    is_active: bool = True


class ExchangeRequest(SchemaBase):
    action: str = Field(min_length=1, max_length=50, description="兑换项标识（exchange: 开头）")
    plan_id: Optional[int] = Field(
        default=None, description="兑换 VIP 时必填：目标套餐 ID（服务端据此真实开通订阅）"
    )


class PointsGrantRequest(SchemaBase):
    user_id: int
    amount: int = Field(gt=0, le=100000, description="变动数额（正数）")
    reason: Optional[str] = Field(default=None, max_length=255)


class PointsStatsOut(SchemaBase):
    total_accounts: int = 0
    total_balance: int = 0
    total_earned: int = 0
    total_spent: int = 0
    transaction_count: int = 0
    active_rules: int = 0
    top_holders: list[LeaderboardItem] = Field(default_factory=list)
