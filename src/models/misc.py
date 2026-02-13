from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from . import Base


class SearchHistory(Base):
    __tablename__ = 'search_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    keyword = Column(String(255), nullable=False)
    results_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'keyword': self.keyword,
            'results_count': self.results_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PageView(Base):
    __tablename__ = 'page_views'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)  # 可选的用户ID，未登录用户为NULL
    session_id = Column(String(255), nullable=True)  # 会话ID，用于追踪未登录用户
    page_url = Column(String(500), nullable=False)  # 访问的页面URL
    page_title = Column(String(500), nullable=True)  # 页面标题
    referrer = Column(String(500), nullable=True)  # 来源页面
    user_agent = Column(String(500), nullable=True)  # 用户代理
    ip_address = Column(String(45), nullable=True)  # IP地址（支持IPv6）
    device_type = Column(String(50), nullable=True)  # 设备类型
    browser = Column(String(100), nullable=True)  # 浏览器类型
    platform = Column(String(100), nullable=True)  # 操作系统平台
    country = Column(String(100), nullable=True)  # 国家
    city = Column(String(100), nullable=True)  # 城市
    created_at = Column(DateTime, default=lambda: datetime.now())  # 访问时间

    # 为常用查询创建索引
    __table_args__ = (
        Index('idx_page_views_user_id', 'user_id'),
        Index('idx_page_views_page_url', 'page_url'),
        Index('idx_page_views_created_at', 'created_at'),
        Index('idx_page_views_session_id', 'session_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'page_url': self.page_url,
            'page_title': self.page_title,
            'referrer': self.referrer,
            'user_agent': self.user_agent,
            'ip_address': self.ip_address,
            'device_type': self.device_type,
            'browser': self.browser,
            'platform': self.platform,
            'country': self.country,
            'city': self.city,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserActivity(Base):
    __tablename__ = 'user_activities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # 用户ID
    activity_type = Column(String(100), nullable=False)  # 活动类型 (e.g., 'view', 'like', 'comment', 'share')
    target_type = Column(String(50), nullable=False)  # 目标类型 (e.g., 'article', 'comment')
    target_id = Column(Integer, nullable=False)  # 目标ID
    details = Column(Text)  # 活动详细信息
    ip_address = Column(String(45), nullable=True)  # IP地址
    user_agent = Column(String(500), nullable=True)  # 用户代理
    created_at = Column(DateTime, default=lambda: datetime.now())  # 活动时间

    # 关系
    user = relationship("User", back_populates="activities", primaryjoin="User.id == foreign(UserActivity.user_id)", overlaps="author,user,user,user", uselist=False)

    # 为常用查询创建索引
    __table_args__ = (
        Index('idx_user_activities_user_id', 'user_id'),
        Index('idx_user_activities_type', 'activity_type'),
        Index('idx_user_activities_target', 'target_type', 'target_id'),
        Index('idx_user_activities_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }