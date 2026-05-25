"""
SQLAlchemy 模型定义 - UserSubscription
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-05-25 10:41:21
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey

from . import Base  # 使用统一的 Base


class UserSubscription(Base):
    """用户订阅记录模型模型"""
    __tablename__ = 'user_subscriptions'

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='订阅 ID')

    user_id = Column(BigInteger, ForeignKey('users.id'), doc='用户 ID')

    plan_id = Column(BigInteger, ForeignKey('subscription_plans.id'), doc='计划 ID')

    status = Column(String(20), default='active', doc='状态 (active, cancelled, expired)')

    current_period_end = Column(DateTime, doc='当前周期结束时间')

    stripe_subscription_id = Column(String(255), nullable=True, doc='Stripe 订阅 ID')

    created_at = Column(DateTime, doc='创建时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'status': self.status,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'stripe_subscription_id': self.stripe_subscription_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<UserSubscription id={self.id}>'
