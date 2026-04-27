"""
SQLAlchemy 模型定义 - VIPSubscription
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float,
                        ForeignKey, Integer, Numeric, String, Text)

from . import Base  # 使用统一的 Base


class VIPSubscription(Base):
    """VIP 订阅模型模型"""
    __tablename__ = 'vip_subscriptions'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    user = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user')


    plan = Column(Integer, ForeignKey('vip_plans.id'), nullable=False, doc='plan')

    starts_at = Column(DateTime, doc='starts_at')

    expires_at = Column(DateTime, doc='expires_at')

    status = Column(BigInteger, default=0, doc='status')

    payment_amount = Column(Numeric(10, 2), nullable=True, doc='payment_amount')

    transaction_id = Column(String(255), nullable=True, doc='transaction_id')

    created_at = Column(DateTime, doc='created_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user': self.user,
            'plan': self.plan,
            'starts_at': self.starts_at.isoformat() if self.starts_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'status': self.status,
            'payment_amount': self.payment_amount,
            'transaction_id': self.transaction_id,
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
        return f'<VIPSubscription id={self.id}>'
