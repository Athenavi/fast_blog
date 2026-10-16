"""vip 模块的请求 / 响应模型"""

import json
from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase


class VipPlanCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    price: float = Field(ge=0)
    original_price: Optional[float] = Field(default=None, ge=0)
    duration_days: int = Field(ge=1, description="有效期天数")
    level: int = Field(default=1, ge=1)
    features: Optional[list[str]] = Field(default=None, description="特权功能（JSON 列表）")
    is_active: bool = True


class VipPlanUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    price: Optional[float] = Field(default=None, ge=0)
    original_price: Optional[float] = Field(default=None, ge=0)
    duration_days: Optional[int] = Field(default=None, ge=1)
    level: Optional[int] = Field(default=None, ge=1)
    features: Optional[list[str]] = None
    is_active: Optional[bool] = None


class VipPlanOut(SchemaBase):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    duration_days: Optional[int] = None
    level: int = 1
    features: Optional[list[str]] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("features", mode="before")
    @classmethod
    def _parse_features(cls, v: object) -> object:
        """DB 列是 JSON 字符串，序列化时转列表"""
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v


class VipFeatureCreate(SchemaBase):
    code: str = Field(min_length=1, max_length=50, pattern="^[a-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    required_level: int = Field(default=1, ge=1)
    is_active: bool = True


class VipFeatureUpdate(SchemaBase):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50, pattern="^[a-z0-9_.-]+$")
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    required_level: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class VipFeatureOut(SchemaBase):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    required_level: int = 1
    is_active: bool = True
    created_at: Optional[datetime] = None


class VipSubscriptionCreate(SchemaBase):
    """管理员手动开通订阅（支付侧由 payment 域后续接入）"""

    user_id: int
    plan_id: int
    starts_at: Optional[datetime] = None
    payment_amount: Optional[float] = None
    transaction_id: Optional[str] = Field(default=None, max_length=255)


class VipSubscriptionOut(SchemaBase):
    id: int
    user_id: Optional[int] = None
    plan_id: Optional[int] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: int = 0
    payment_amount: Optional[float] = None
    transaction_id: Optional[str] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------- 前台公开读（/vip 页）
class PublicPlanOut(SchemaBase):
    """前台 /vip 页的上架套餐（不含时间戳等管理字段）

    ``features`` 是合并后的权益字符串数组：套餐自身 ``features`` JSON 列表在前，
    后接按等级匹配到的 ``VIPFeature`` 展示名（去重、保序），
    合并规则见 ``service.public_plans``。
    """

    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    duration_days: Optional[int] = None
    level: int = 1
    features: list[str] = Field(default_factory=list)

    @field_validator("features", mode="before")
    @classmethod
    def _parse_features(cls, v: object) -> object:
        """DB 列是 JSON 字符串（可为 NULL），序列化时转列表，空值统一为 []"""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                return [v]
        if v is None:
            return []
        return v if isinstance(v, list) else [str(v)]
