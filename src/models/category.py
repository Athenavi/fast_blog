from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from . import Base  # 使用统一的Base


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(),
                        onupdate=lambda: datetime.now())

    # 关系定义
    subscriptions = relationship('CategorySubscription', back_populates='category', lazy='select', primaryjoin="CategorySubscription.category_id == foreign(Category.id)",
                                 overlaps="articles,author,custom_fields,email_subscription,media,notifications,recipient,subscriber,user,vip_subscriptions")
    articles = relationship('Article', back_populates='category', lazy='select', primaryjoin="Article.category_id == foreign(Category.id)", overlaps="subscriptions")


class CategorySubscription(Base):
    __tablename__ = 'category_subscriptions'
    id = Column(Integer, primary_key=True)
    subscriber_id = Column(Integer, nullable=False)
    category_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now())

    # 关系定义
    subscriber = relationship('User', back_populates='category_subscriptions', primaryjoin="CategorySubscription.subscriber_id == foreign(User.id)",
                             overlaps="articles,author,custom_fields,email_subscription,media,notifications,recipient,user,vip_subscriptions")
    category = relationship('Category', back_populates='subscriptions', primaryjoin="CategorySubscription.category_id == foreign(Category.id)",
                           overlaps="articles,category,subscriptions")

    __table_args__ = (
        Index('idx_category_subscriptions_subscriber', 'subscriber_id'),
        Index('idx_category_subscriptions_category', 'category_id'),
        UniqueConstraint('subscriber_id', 'category_id', name='uq_category_subscriptions')
    )