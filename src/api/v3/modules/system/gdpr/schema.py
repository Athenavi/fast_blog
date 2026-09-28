"""gdpr 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class GDPRConsentOut(SchemaBase):
    id: int
    user_id: Optional[int] = None
    consent_type: Optional[str] = None
    granted: bool = False
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None


class GDPRStatsOut(SchemaBase):
    total: int = 0
    granted: int = 0
    revoked: int = 0
    by_type: dict[str, int] = Field(default_factory=dict, description="按 consent_type 分组计数")


class GDPRConsentCreate(SchemaBase):
    """同意 / 撤回上报（未登录访客也可上报 Cookie 同意）"""

    consent_type: str = Field(
        default="cookies", max_length=50, description="同意类型：cookies / analytics / marketing"
    )
    granted: bool = Field(description="true=同意，false=撤回")
    details: Optional[str] = Field(default=None, max_length=2000, description="附加说明")
