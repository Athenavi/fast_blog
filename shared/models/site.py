"""
SQLAlchemy 模型定义 - Site
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-05-08 10:43:26
"""


from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime

from . import Base  # 使用统一的 Base

from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, Index

class Site(Base):
    """站点模型（多站点支持）模型"""
    __tablename__ = 'sites'



    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    name = Column(String(200), nullable=True, doc='name')


    slug = Column(String(100), unique=True, nullable=True, doc='slug')


    domain = Column(String(255), index=True, nullable=True, doc='domain')


    path = Column(String(255), default='/', nullable=True, doc='path')


    is_active = Column(Boolean, default=True, doc='is_active')


    is_default = Column(Boolean, default=False, doc='is_default')


    settings = Column(String(255), nullable=True, doc='settings')


    theme = Column(String(100), default='default', doc='theme')


    language = Column(String(10), default='zh-CN', doc='language')


    timezone = Column(String(50), default='Asia/Shanghai', doc='timezone')


    title = Column(String(200), nullable=True, doc='title')


    description = Column(Text, nullable=True, doc='description')


    keywords = Column(String(500), nullable=True, doc='keywords')


    admin_user_id = Column(BigInteger, nullable=True, doc='admin_user_id')


    created_at = Column(DateTime, doc='created_at')


    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_sites_domain', 'domain'),
        Index('idx_sites_slug', 'slug', unique=True),
        Index('idx_sites_is_active', 'is_active'),
        Index('idx_sites_is_default', 'is_default'),

    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'domain': self.domain,
            'path': self.path,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'settings': self.settings,
            'theme': self.theme,
            'language': self.language,
            'timezone': self.timezone,
            'title': self.title,
            'description': self.description,
            'keywords': self.keywords,
            'admin_user_id': self.admin_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Site id={self.id}>'
