"""
SQLAlchemy 模型定义 - Site
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-05-09 11:47:19
"""

from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, Index

from . import Base  # 使用统一的 Base


class Site(Base):
    """站点模型（多站点支持）模型"""
    __tablename__ = 'sites'


    __table_args__ = (
        Index('idx_sites_domain', 'domain'),
        Index('idx_sites_slug', 'slug', unique=True),
        Index('idx_sites_is_active', 'is_active'),
        Index('idx_sites_is_default', 'is_default'),
    )


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='站点 ID')

    name = Column(String(200), nullable=True, doc='站点名称')

    slug = Column(String(100), unique=True, nullable=True, doc='站点标识')

    domain = Column(String(255), index=True, nullable=True, doc='域名（如 example.com）')

    path = Column(String(255), default='/', nullable=True, doc='路径前缀（如 /site1）')

    is_active = Column(Boolean, default=True, doc='是否激活')


    is_default = Column(Boolean, default=False, doc='是否为默认站点')


    settings = Column(String(255), nullable=True, doc='站点设置（JSON格式）')

    theme = Column(String(100), default='default', doc='主题slug')

    language = Column(String(10), default='zh-CN', doc='语言代码')

    timezone = Column(String(50), default='Asia/Shanghai', doc='时区')

    title = Column(String(200), nullable=True, doc='站点标题')

    description = Column(Text, nullable=True, doc='站点描述')


    keywords = Column(String(500), nullable=True, doc='关键词')

    admin_user_id = Column(BigInteger, nullable=True, doc='站点管理员ID')


    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')


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

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Site id={self.id}>'


