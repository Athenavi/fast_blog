from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index, Numeric
from sqlalchemy.orm import relationship

from . import Base  # 使用统一的Base


class VIPPlan(Base):
    """VIP套餐表"""
    __tablename__ = 'vip_plans'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # 套餐名称
    description = Column(Text)  # 套餐描述
    price = Column(Numeric(10, 2), nullable=False)  # 价格
    original_price = Column(Numeric(10, 2))  # 原价，用于显示折扣
    duration_days = Column(Integer, nullable=False)  # 有效期天数
    level = Column(Integer, default=1, nullable=False)  # VIP等级
    features = Column(Text)  # 特权功能JSON
    is_active = Column(Boolean, default=True)  # 是否激活
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<VIPPlan {self.name}>'


class VIPSubscription(Base):
    """VIP订阅记录表"""
    __tablename__ = 'vip_subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    plan_id = Column(Integer, nullable=False)
    starts_at = Column(DateTime, nullable=False)  # 开始时间
    expires_at = Column(DateTime, nullable=False)  # 过期时间
    status = Column(Integer, default=0, nullable=False)
    payment_amount = Column(Numeric(10, 2))  # 实际支付金额
    transaction_id = Column(String(255))  # 支付交易ID
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # 关系定义
    user = relationship('User', back_populates='vip_subscriptions', primaryjoin="VIPSubscription.user_id == foreign(User.id)",
                        overlaps="articles,author,category_subscriptions,custom_fields,email_subscription,media,notifications,recipient,subscriber,user")
    plan = relationship('VIPPlan', primaryjoin="VIPSubscription.plan_id == foreign(VIPPlan.id)",
                       overlaps="user")

    __table_args__ = (
        Index('idx_vip_subscriptions_user_id', 'user_id'),
        Index('idx_vip_subscriptions_expires_at', 'expires_at'),
        Index('idx_vip_subscriptions_transaction_id', 'transaction_id'),
        Index('idx_vip_subscriptions_status', 'status'),
    )

    def __repr__(self):
        return f'<VIPSubscription user_id={self.user_id} plan_id={self.plan_id}>'


class VIPFeature(Base):
    """VIP功能特权表"""
    __tablename__ = 'vip_features'

    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)  # 功能代码
    name = Column(String(100), nullable=False)  # 功能名称
    description = Column(Text)  # 功能描述
    required_level = Column(Integer, default=1)  # 所需VIP等级
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<VIPFeature {self.name}>'