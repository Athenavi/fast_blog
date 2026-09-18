"""log 模块的请求 / 响应模型"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class AuditLogOut(SchemaBase):
    id: Optional[int] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    action: Optional[str] = None
    level: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[Any] = None


class AuditCleanupRequest(SchemaBase):
    days: int = Field(default=90, ge=1, le=3650, description="保留最近 N 天，更早的删除")


class AuditExportResult(SchemaBase):
    format: str
    content: str
    count: int = 0


class LockedUserOut(SchemaBase):
    username: Optional[str] = None
    failed_attempts: Optional[int] = None
    locked_until: Optional[str] = None
    last_attempt: Optional[str] = None


class LoginHistoryOut(SchemaBase):
    username: str
    history: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class SecurityStatsOut(SchemaBase):
    username: str
    stats: Dict[str, Any] = Field(default_factory=dict)
