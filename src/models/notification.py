from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index
from sqlalchemy.orm import relationship

from . import Base  # 使用统一的Base


class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True)
    recipient_id = Column(Integer, nullable=False)
    type = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, default=None)
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())

    # 关系定义
    recipient = relationship('User', back_populates='notifications', primaryjoin="Notification.recipient_id == foreign(User.id)",
                             overlaps="articles,author,media,subscriber,user,vip_subscriptions")

    __table_args__ = (
        Index('idx_recipient_id_noti', 'recipient_id'),
    )