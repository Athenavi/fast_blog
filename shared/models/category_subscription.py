"""
SQLAlchemy 模型定义 - CategorySubscription
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class CategorySubscription(Base):
    """分类订阅模型模型"""
    __tablename__ = 'category_subscriptions'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    category = Column(BigInteger, ForeignKey('categories.id'), nullable=False, doc='category')


    subscriber = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='subscriber')


    created_at = Column(DateTime, doc='created_at')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'category': self.category,
            'subscriber': self.subscriber,
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
        return f'<CategorySubscription id={self.id}>'
