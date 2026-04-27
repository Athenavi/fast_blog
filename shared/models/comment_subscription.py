"""
SQLAlchemy 模型定义 - CommentSubscription
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)

from . import Base  # 使用统一的 Base


class CommentSubscription(Base):
    """评论订阅模型模型"""
    __tablename__ = 'comment_subscriptions'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    article_id = Column(BigInteger, index=True, doc='article_id')


    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='user_id')

    email = Column(String(255), nullable=True, doc='email')

    notify_type = Column(String(255), default='new_comment', doc='notify_type')

    is_active = Column(Boolean, default=True, doc='is_active')

    confirm_token = Column(String(64), nullable=True, doc='confirm_token')

    confirmed_at = Column(DateTime, nullable=True, doc='confirmed_at')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_comment_subscriptions_article', 'article_id'),
        Index('idx_comment_subscriptions_email', 'email'),
        Index('idx_comment_subscriptions_user', 'user_id'),
        Index('idx_comment_subscriptions_unique', 'article_id', 'email', unique=True),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'article_id': self.article_id,
            'user_id': self.user_id,
            'email': self.email,
            'notify_type': self.notify_type,
            'is_active': self.is_active,
            'confirm_token': self.confirm_token,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<CommentSubscription id={self.id}>'
