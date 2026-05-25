"""
SQLAlchemy 模型定义 - SubscriptionPlan
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-05-25 10:41:21
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime

from . import Base  # 使用统一的 Base


class SubscriptionPlan(Base):
    """会员订阅计划模型模型"""
    __tablename__ = 'subscription_plans'

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='计划 ID')

    name = Column(String(255), nullable=True, doc='计划名称')

    slug = Column(String(255), unique=True, nullable=True, doc='唯一标识符')

    price = Column(Integer, doc='价格 (分)')

    interval = Column(String(20), default='month', doc='计费周期 (month, year)')

    features_json = Column(Text, nullable=False, doc='功能列表 JSON')

    is_active = Column(Boolean, default=True, doc='是否启用')

    stripe_price_id = Column(String(255), nullable=True, doc='Stripe 价格 ID')

    created_at = Column(DateTime, doc='创建时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'price': self.price,
            'interval': self.interval,
            'features_json': self.features_json,
            'is_active': self.is_active,
            'stripe_price_id': self.stripe_price_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<SubscriptionPlan id={self.id}>'
