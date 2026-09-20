"""payment 模块的请求 / 响应模型

四类资源：支付网关（gateway）、支付交易（transaction）、加密货币支付（crypto）、税务配置（tax）。

约定：
  - ``PaymentGateway.config_data`` 是库里的 JSON 字符串列，**只入不出** —— 出参只给
    ``has_config_data`` 布尔位（与 ``ops/email``、``ai/config`` 的凭据约定一致），
    更新时不传该字段即保持原值；
  - ``PaymentTransaction.extra_metadata`` 同样是 JSON 字符串列（ORM 属性 ``extra_metadata``，
    库列名 ``metadata``）：入参 ``dict``、落库 ``json.dumps``、出参用
    ``field_validator(mode="before")`` 解析回对象（同模式见 ``marketing/vip`` 的 ``features``）；
  - 金额列是 ``Numeric(10, 2)``，出参统一按 ``float`` 暴露。
"""

import json
from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase


def _loads_or_none(value: object) -> object:
    """JSON 字符串 → 对象；脏数据回退 None，避免列表接口 500"""
    if value is None or isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except ValueError:
            return None
        return parsed if isinstance(parsed, (dict, list)) else None
    return None


# ---------------------------------------------------------------- 支付网关
class PaymentGatewayCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=50, description="stripe / paypal / alipay / wechat / crypto")
    config_data: Optional[dict] = Field(default=None, description="网关配置（只入不出）")
    is_active: bool = False
    supported_currencies: str = Field(default="USD,CNY", max_length=255)


class PaymentGatewayUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    provider: Optional[str] = Field(default=None, min_length=1, max_length=50)
    config_data: Optional[dict] = None
    is_active: Optional[bool] = None
    supported_currencies: Optional[str] = Field(default=None, max_length=255)


class PaymentGatewayOut(SchemaBase):
    id: int
    name: Optional[str] = None
    provider: Optional[str] = None
    is_active: bool = False
    supported_currencies: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 支付交易
class PaymentTransactionCreate(SchemaBase):
    user: int = Field(description="用户 ID")
    amount: float = Field(gt=0, description="金额")
    gateway: Optional[int] = Field(default=None, description="支付网关 ID")
    order_id: Optional[str] = Field(default=None, max_length=100)
    currency: str = Field(default="USD", max_length=3)
    status: str = Field(default="pending", max_length=20)
    transaction_id: Optional[str] = Field(default=None, max_length=100)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    extra_metadata: Optional[dict] = Field(default=None, description="附加元数据（JSON 对象）")


class PaymentTransactionUpdate(SchemaBase):
    amount: Optional[float] = Field(default=None, gt=0)
    gateway: Optional[int] = None
    order_id: Optional[str] = Field(default=None, max_length=100)
    currency: Optional[str] = Field(default=None, max_length=3)
    status: Optional[str] = Field(default=None, max_length=20)
    transaction_id: Optional[str] = Field(default=None, max_length=100)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    extra_metadata: Optional[dict] = None


class PaymentTransactionOut(SchemaBase):
    id: int
    user: Optional[int] = None
    order_id: Optional[str] = None
    gateway: Optional[int] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    transaction_id: Optional[str] = None
    payment_method: Optional[str] = None
    extra_metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("extra_metadata", mode="before")
    @classmethod
    def _parse_extra_metadata(cls, value: object) -> object:
        return _loads_or_none(value)


# ---------------------------------------------------------------- 加密货币支付
class CryptoPaymentCreate(SchemaBase):
    transaction: int = Field(description="关联的支付交易 ID")
    wallet_address: str = Field(min_length=1, max_length=255)
    blockchain: str = Field(min_length=1, max_length=50, description="ethereum / bitcoin ...")
    token_symbol: str = Field(min_length=1, max_length=10, description="ETH / BTC / USDT ...")
    tx_hash: Optional[str] = Field(default=None, max_length=255)
    confirmations: int = Field(default=0, ge=0)
    required_confirmations: int = Field(default=6, ge=0)
    exchange_rate: Optional[float] = None
    crypto_amount: Optional[float] = None
    status: str = Field(default="waiting_payment", max_length=20)
    expires_at: Optional[datetime] = None


class CryptoPaymentUpdate(SchemaBase):
    wallet_address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    blockchain: Optional[str] = Field(default=None, min_length=1, max_length=50)
    token_symbol: Optional[str] = Field(default=None, min_length=1, max_length=10)
    tx_hash: Optional[str] = Field(default=None, max_length=255)
    confirmations: Optional[int] = Field(default=None, ge=0)
    required_confirmations: Optional[int] = Field(default=None, ge=0)
    exchange_rate: Optional[float] = None
    crypto_amount: Optional[float] = None
    status: Optional[str] = Field(default=None, max_length=20)
    expires_at: Optional[datetime] = None


class CryptoPaymentOut(SchemaBase):
    id: int
    transaction: Optional[int] = None
    wallet_address: Optional[str] = None
    blockchain: Optional[str] = None
    token_symbol: Optional[str] = None
    tx_hash: Optional[str] = None
    confirmations: int = 0
    required_confirmations: int = 6
    exchange_rate: Optional[float] = None
    crypto_amount: Optional[float] = None
    status: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 税务配置
class TaxConfigCreate(SchemaBase):
    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2 国家代码")
    tax_type: str = Field(min_length=1, max_length=50, description="VAT / GST / Sales Tax ...")
    rate: float = Field(ge=0, description="税率（百分比）")
    region: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = True
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class TaxConfigUpdate(SchemaBase):
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    tax_type: Optional[str] = Field(default=None, min_length=1, max_length=50)
    rate: Optional[float] = Field(default=None, ge=0)
    region: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class TaxConfigOut(SchemaBase):
    id: int
    country: Optional[str] = None
    region: Optional[str] = None
    tax_type: Optional[str] = None
    rate: Optional[float] = None
    description: Optional[str] = None
    is_active: bool = True
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 发起支付 / 回调
class PaymentInitiateRequest(SchemaBase):
    """发起支付（委托给具支付能力的插件，与 v2 ``POST /shop/admin/create`` 同语义）"""

    order_id: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    subject: str = Field(default="", max_length=255)
    gateway: Optional[int] = Field(default=None, description="指定支付网关，缺省用当前激活网关")
    return_url: Optional[str] = Field(default=None, max_length=500)
    cancel_url: Optional[str] = Field(default=None, max_length=500)
    notify_url: Optional[str] = Field(default=None, max_length=500)
