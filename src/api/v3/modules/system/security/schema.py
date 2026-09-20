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
