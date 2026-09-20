"""mobile.revenue 模块的请求模型

用户端不接收 ``user_id``（一律取登录用户），因此请求体比管理端少一个字段。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class MobilePayoutCreate(SchemaBase):
    amount: float = Field(gt=0, description="提现金额")
    payment_method: str = Field(min_length=1, max_length=50, description="alipay / wechat / bank_transfer")
    payment_account: str = Field(min_length=1, max_length=200)
    account_name: Optional[str] = Field(default=None, max_length=100)
