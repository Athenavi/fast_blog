"""approval 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class ApprovalRecordCreate(SchemaBase):
    """提交内容进入审批流（由发布流程/API 触发）"""

    content_type: str = Field(default="article", max_length=50, description="内容类型（article/page/…）")
    content_id: int
    max_level: int = Field(default=1, ge=1, le=5, description="审批级数")


class ApprovalRecordOut(SchemaBase):
    id: int
    content_type: Optional[str] = None
    content_id: Optional[int] = None
    applicant_id: Optional[int] = None
    current_level: int = 1
    max_level: int = 1
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ApprovalStepOut(SchemaBase):
    id: int
    record_id: int
    level: int
    approver_id: Optional[int] = None
    action: Optional[str] = None
    comment: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ApprovalDecisionRequest(SchemaBase):
    action: str = Field(pattern="^(approve|reject)$", description="approve 通过 / reject 驳回")
    comment: Optional[str] = None
