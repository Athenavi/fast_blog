"""enterprise 模块的请求 / 响应模型

企业许可证（license）与数据保留策略（data retention policy）。
``features`` 列在库中是 JSON 字符串：入参为 ``list[str]``、落库 ``json.dumps``、
出参经 ``field_validator(mode="before")`` 解析回列表（样板见 vip schema）。
"""

import json
from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase


# ---------------------------------------------------------------- 企业许可证
class EnterpriseLicenseCreate(SchemaBase):
    license_key: str = Field(min_length=1, max_length=255)
    license_type: str = Field(default="professional", max_length=50)
    company_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    max_sites: int = Field(default=-1, ge=-1, description="最大站点数（-1 表示无限）")
    features: Optional[list[str]] = Field(default=None, description="功能列表（JSON 列表）")
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True
    support_level: str = Field(default="standard", max_length=50)
    sla_enabled: bool = False
    sla_uptime_guarantee: Optional[float] = Field(
        default=None, ge=0, le=100, description="SLA 可用性保证（如 99.9）"
    )


class EnterpriseLicenseUpdate(SchemaBase):
    license_key: Optional[str] = Field(default=None, min_length=1, max_length=255)
    license_type: Optional[str] = Field(default=None, max_length=50)
    company_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    max_sites: Optional[int] = Field(default=None, ge=-1)
    features: Optional[list[str]] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None
    support_level: Optional[str] = Field(default=None, max_length=50)
    sla_enabled: Optional[bool] = None
    sla_uptime_guarantee: Optional[float] = Field(default=None, ge=0, le=100)


class EnterpriseLicenseOut(SchemaBase):
    id: int
    license_key: Optional[str] = None
    license_type: str = "professional"
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    max_sites: int = -1
    features: Optional[list[str]] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True
    support_level: str = "standard"
    sla_enabled: bool = False
    sla_uptime_guarantee: Optional[float] = None
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


# ---------------------------------------------------------------- 数据保留策略
class DataRetentionPolicyCreate(SchemaBase):
    data_category: str = Field(
        min_length=1, max_length=50, description="数据类别（如 audit_log/notification/analytics）"
    )
    retention_days: int = Field(ge=1, description="保留天数")
    action: str = Field(default="delete", max_length=50, description="到期动作（delete/archive）")
    is_active: bool = True


class DataRetentionPolicyUpdate(SchemaBase):
    data_category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    retention_days: Optional[int] = Field(default=None, ge=1)
    action: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None


class DataRetentionPolicyOut(SchemaBase):
    id: int
    data_category: str
    retention_days: int
    action: str = "delete"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
