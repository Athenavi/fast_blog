"""
SQLAlchemy 模型定义 - PageView
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-06-13 23:12:16
"""

from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class PageView(Base):
    """页面浏览模型模型"""
    __tablename__ = 'page_views'
    # 手工补充的索引：page_views 是「每次访问写一行」的热表，分析查询基本都按
    # created_at / user 过滤与聚合，无索引会退化为全表扫描。
    # （模型由生成器产出，若重新生成请同步 config/models.yaml 的 indexes 段。）
    __table_args__ = (
        Index('idx_page_views_created_at', 'created_at'),
        Index('idx_page_views_user_created', 'user', 'created_at'),
        Index('idx_page_views_session', 'session_id'),
    )




    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='浏览 ID')

    user = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='用户')


    session_id = Column(String(255), nullable=True, doc='会话 ID')

    page_url = Column(String(500), nullable=True, doc='页面 URL')

    page_title = Column(String(500), nullable=True, doc='页面标题')

    referrer = Column(String(500), nullable=True, doc='来源页面')

    user_agent = Column(String(500), nullable=True, doc='用户代理')

    ip_address = Column(String(45), nullable=True, doc='IP 地址')

    device_type = Column(String(50), nullable=True, doc='设备类型')

    browser = Column(String(100), nullable=True, doc='浏览器类型')

    platform = Column(String(100), nullable=True, doc='操作系统平台')

    country = Column(String(100), nullable=True, doc='国家')

    city = Column(String(100), nullable=True, doc='城市')

    created_at = Column(DateTime, doc='访问时间')


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

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<PageView id={self.id}>'


