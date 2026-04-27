"""
SQLAlchemy 模型定义 - Form
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Index, Integer,
                        String, Text)

from . import Base  # 使用统一的 Base


class Form(Base):
    """表单模型模型"""
    __tablename__ = 'forms'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    title = Column(String(255), nullable=True, doc='title')


    slug = Column(String(255), unique=True, nullable=True, doc='slug')


    description = Column(String(255), nullable=True, doc='description')

    status = Column(String(255), default='draft', doc='status')

    submit_message = Column(String(255), nullable=True, doc='submit_message')

    email_notification = Column(Boolean, default=False, doc='email_notification')

    notification_email = Column(String(255), nullable=True, doc='notification_email')

    store_submissions = Column(Boolean, default=True, doc='store_submissions')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')

    published_at = Column(DateTime, nullable=True, doc='published_at')


    __table_args__ = (

    Index('idx_forms_slug', 'slug', unique=True),
        Index('idx_forms_status', 'status'),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'description': self.description,
            'status': self.status,
            'submit_message': self.submit_message,
            'email_notification': self.email_notification,
            'notification_email': self.notification_email,
            'store_submissions': self.store_submissions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Form id={self.id}>'
