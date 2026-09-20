"""
SQLAlchemy 模型定义 - CertificationReview
手写模型（T5-11 批次 13），写法对齐代码生成器产物。

认证**审核流水**：每次通过 / 驳回 / 撤销都追加一条，用于追溯"谁在什么时候改成了什么"。
v2 完全没有这层（内存实现只改一个字段，历史不可查）。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class CertificationReview(Base):
    """认证审核流水模型"""
    __tablename__ = 'certification_reviews'

    __table_args__ = (Index('idx_certification_reviews_cert', 'certification_id', 'created_at'),)

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='记录 ID')

    certification_id = Column(
        BigInteger, ForeignKey('expert_certifications.id', ondelete='CASCADE'),
        nullable=False, doc='认证 ID',
    )

    reviewer_id = Column(BigInteger, nullable=True, doc='审核人 ID（申请人撤回时为空）')

    action = Column(String(20), doc='动作：approve / reject / revoke / withdraw / submit')

    comment = Column(String(500), nullable=True, doc='意见')

    created_at = Column(DateTime, doc='发生时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'certification_id': self.certification_id,
            'reviewer_id': self.reviewer_id,
            'action': self.action,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<CertificationReview cert={self.certification_id} action={self.action}>'
