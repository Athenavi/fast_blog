"""
SQLAlchemy 模型定义 - ExpertCertification
手写模型（T5-11 批次 13），写法对齐代码生成器产物。

专家认证**主表**：一名用户在同一时刻只应有一条**有效**认证（见 ``idx_expert_certifications_user_status``）。

状态机：``pending``（待审）→ ``approved``（通过）/ ``rejected``（驳回）；
``approved`` → ``revoked``（撤销）。通过时写入 ``issued_at`` 与 ``expires_at``（两年有效期）。

> ``id_number`` 是敏感字段，``to_dict()`` 默认排除（``exclude_sensitive=True``）。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Text

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class ExpertCertification(Base):
    """专家认证模型"""
    __tablename__ = 'expert_certifications'

    __table_args__ = (
        Index('idx_expert_certifications_user_status', 'user_id', 'status'),
        Index('idx_expert_certifications_status', 'status'),
        Index('idx_expert_certifications_type', 'cert_type'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='认证 ID')

    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='申请人 ID')

    cert_type = Column(String(50), nullable=False, doc='认证类型')

    status = Column(String(20), default='pending', doc='状态：pending / approved / rejected / revoked')

    # ---- 实名信息（属于敏感数据）----
    real_name = Column(String(100), doc='真实姓名')
    id_number = Column(String(64), doc='证件号码（敏感，to_dict 默认排除）')
    phone = Column(String(32), doc='联系电话')
    email = Column(String(255), doc='联系邮箱')

    # ---- 资质信息 ----
    organization = Column(String(255), doc='所在机构')
    position = Column(String(100), doc='职务')
    department = Column(String(100), doc='部门')
    work_years = Column(Integer, default=0, doc='从业年限')
    intro = Column(Text, doc='个人简介')
    achievements = Column(Text, doc='代表成果')
    portfolio_url = Column(String(500), doc='作品集 / 主页链接')

    # ---- 流转 ----
    applied_at = Column(DateTime, doc='申请时间')
    reviewed_at = Column(DateTime, nullable=True, doc='最近审核时间')
    reviewer_id = Column(BigInteger, nullable=True, doc='最近审核人 ID')
    review_comment = Column(String(500), nullable=True, doc='审核意见')
    issued_at = Column(DateTime, nullable=True, doc='通过时间')
    expires_at = Column(DateTime, nullable=True, doc='有效期至（通过后两年）')

    created_at = Column(DateTime, doc='创建时间')
    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（证件号等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'cert_type': self.cert_type,
            'status': self.status,
            'real_name': self.real_name,
            'phone': self.phone,
            'email': self.email,
            'organization': self.organization,
            'position': self.position,
            'department': self.department,
            'work_years': self.work_years,
            'intro': self.intro,
            'achievements': self.achievements,
            'portfolio_url': self.portfolio_url,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewer_id': self.reviewer_id,
            'review_comment': self.review_comment,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
                'id_number': self.id_number,
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<ExpertCertification id={self.id} user={self.user_id} status={self.status}>'
