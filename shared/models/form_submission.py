"""
SQLAlchemy 模型定义 - FormSubmission
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)

from . import Base  # 使用统一的 Base


class FormSubmission(Base):
    """表单提交记录模型模型"""
    __tablename__ = 'form_submissions'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    form_id = Column(BigInteger, ForeignKey('forms.id'), nullable=False, doc='form_id')


    data = Column(String(255), nullable=True, doc='data')


    ip_address = Column(String(45), nullable=True, doc='ip_address')

    user_agent = Column(String(255), nullable=True, doc='user_agent')

    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='user_id')

    status = Column(String(255), default='new', doc='status')

    created_at = Column(DateTime, doc='created_at')


    __table_args__ = (

    Index('idx_form_submissions_form_id', 'form_id'),
        Index('idx_form_submissions_status', 'status'),
        Index('idx_form_submissions_created', 'created_at'),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'form_id': self.form_id,
            'data': self.data,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<FormSubmission id={self.id}>'
