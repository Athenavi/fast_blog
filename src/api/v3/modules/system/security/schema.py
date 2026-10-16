"""security 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class SecurityOverviewOut(SchemaBase):
    attempts_24h: int = 0
    failures_24h: int = 0
    success_rate: float = 0.0
    locked_users: int = 0
    blacklist_count: int = 0
    top_failure_reasons: dict[str, int] = Field(default_factory=dict)


class LoginAttemptOut(SchemaBase):
    id: int
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_success: bool = False
    failure_reason: Optional[str] = None
    created_at: Optional[datetime] = None


class BlacklistOut(SchemaBase):
    id: int
    token_identifier: Optional[str] = None
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SecurityReportArchiveRequest(SchemaBase):
    """归档一份安全周期报表（写入 ``report_history``）"""

    kind: str = Field(default="weekly", description="weekly / monthly")


class AnomalyThresholdUpdate(SchemaBase):
    """异常行为检测阈值（增量更新；未提供的项保持原值，未知项会被拒绝）"""

    brute_force_failures: Optional[int] = Field(default=None, ge=1, le=1000)
    brute_force_window_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    spray_usernames: Optional[int] = Field(default=None, ge=2, le=1000)
    spray_window_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    unusual_hour_start: Optional[int] = Field(default=None, ge=0, le=23)
    unusual_hour_end: Optional[int] = Field(default=None, ge=0, le=23)
    unusual_hour_logins: Optional[int] = Field(default=None, ge=1, le=1000)
    unusual_hour_window_hours: Optional[int] = Field(default=None, ge=1, le=720)
    rate_abuse_actions: Optional[int] = Field(default=None, ge=1, le=100000)
    rate_abuse_window_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    max_items: Optional[int] = Field(default=None, ge=1, le=500)
