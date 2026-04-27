"""
SQLAlchemy 模型定义 - PageView
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class PageView(Base):
    """页面浏览模型模型"""
    __tablename__ = 'page_views'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    user = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='user')


    session_id = Column(String(255), nullable=True, doc='session_id')

    page_url = Column(String(500), nullable=True, doc='page_url')

    page_title = Column(String(500), nullable=True, doc='page_title')

    referrer = Column(String(500), nullable=True, doc='referrer')

    user_agent = Column(String(500), nullable=True, doc='user_agent')

    ip_address = Column(String(45), nullable=True, doc='ip_address')

    device_type = Column(String(50), nullable=True, doc='device_type')

    browser = Column(String(100), nullable=True, doc='browser')

    platform = Column(String(100), nullable=True, doc='platform')

    country = Column(String(100), nullable=True, doc='country')

    city = Column(String(100), nullable=True, doc='city')

    created_at = Column(DateTime, doc='created_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user': self.user,
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
        return f'<PageView id={self.id}>'
