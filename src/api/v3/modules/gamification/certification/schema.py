"""certification 模块的请求 / 响应模型

状态机：``pending`` 待审 → ``approved`` 通过 / ``rejected`` 驳回；``approved`` → ``revoked`` 撤销。
通过时写入 ``issued_at`` 与 ``expires_at``，**有效期为两年**（``VALIDITY_YEARS``）。

``id_number``（证件号）属敏感字段：申请时收、对外**不回显**（``CertificationOut`` 不含该字段）。
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: 认证类型：(code, 名称)
CERT_TYPES: tuple[tuple[str, str], ...] = (
    ("professional", "行业专家"),
    ("academic", "学术研究"),
    ("technical", "技术专家"),
    ("media", "媒体从业"),
    ("medical", "医疗健康"),
    ("legal", "法律合规"),
    ("creative", "创意设计"),
)

#: 合法状态
STATUSES: tuple[str, ...] = ("pending", "approved", "rejected", "revoked")

#: 通过后有效期（年）
VALIDITY_YEARS = 2

#: 单次申请最多附带的材料数
MAX_DOCUMENTS = 10


class CertTypeOut(SchemaBase):
    code: str
    name: str


class CertificationDocumentOut(SchemaBase):
    id: int
    file_name: Optional[str] = None
    file_url: str
    file_type: Optional[str] = None
    file_size: int = 0
    created_at: Optional[datetime] = None


class CertificationDocumentIn(SchemaBase):
    """材料**只提交媒体库里的文件引用**（不在这里传二进制）"""

    file_url: str = Field(min_length=1, max_length=500)
    file_name: Optional[str] = Field(default=None, max_length=255)
    file_type: Optional[str] = Field(default=None, max_length=50)
    file_size: int = Field(default=0, ge=0)


class CertificationOut(SchemaBase):
    """对外视图 —— **不含** ``id_number``"""

    id: int
    user_id: int
    username: Optional[str] = None
    cert_type: str
    cert_type_name: Optional[str] = None
    status: str
    real_name: Optional[str] = None
    organization: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    work_years: int = 0
    intro: Optional[str] = None
    achievements: Optional[str] = None
    portfolio_url: Optional[str] = None
    applied_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_expired: bool = False
    documents: list[CertificationDocumentOut] = Field(default_factory=list)


class CertificationApplyRequest(SchemaBase):
    cert_type: str = Field(min_length=1, max_length=50)
    real_name: str = Field(min_length=1, max_length=100)
    id_number: Optional[str] = Field(default=None, max_length=64, description="证件号（仅审核用，不回显）")
    phone: Optional[str] = Field(default=None, max_length=32)
    email: Optional[str] = Field(default=None, max_length=255)
    organization: Optional[str] = Field(default=None, max_length=255)
    position: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=100)
    work_years: int = Field(default=0, ge=0, le=80)
    intro: Optional[str] = Field(default=None, max_length=2000)
    achievements: Optional[str] = Field(default=None, max_length=4000)
    portfolio_url: Optional[str] = Field(default=None, max_length=500)
    documents: list[CertificationDocumentIn] = Field(default_factory=list, max_length=MAX_DOCUMENTS)


class CertificationUpdateRequest(SchemaBase):
    """待审状态下可补充 / 修改的资料（``cert_type`` 也可改）"""

    cert_type: Optional[str] = Field(default=None, max_length=50)
    real_name: Optional[str] = Field(default=None, max_length=100)
    id_number: Optional[str] = Field(default=None, max_length=64)
    phone: Optional[str] = Field(default=None, max_length=32)
    email: Optional[str] = Field(default=None, max_length=255)
    organization: Optional[str] = Field(default=None, max_length=255)
    position: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=100)
    work_years: Optional[int] = Field(default=None, ge=0, le=80)
    intro: Optional[str] = Field(default=None, max_length=2000)
    achievements: Optional[str] = Field(default=None, max_length=4000)
    portfolio_url: Optional[str] = Field(default=None, max_length=500)


class CertificationReviewRequest(SchemaBase):
    approve: bool = Field(description="true = 通过，false = 驳回")
    comment: Optional[str] = Field(default=None, max_length=500)


class CertificationActionRequest(SchemaBase):
    """撤销 / 撤回等只带一句说明的动作"""

    comment: Optional[str] = Field(default=None, max_length=500)


class CertificationReviewOut(SchemaBase):
    id: int
    certification_id: int
    reviewer_id: Optional[int] = None
    action: Optional[str] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class CertificationStatsOut(SchemaBase):
    total: int = 0
    pending: int = 0
    approved: int = 0
    rejected: int = 0
    revoked: int = 0
    expiring_soon: int = 0
    expired: int = 0
    by_type: list[dict] = Field(default_factory=list)
