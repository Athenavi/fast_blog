"""
SQLAlchemy 模型定义 - Plugin
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, Index,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class Plugin(Base):
    """插件模型模型"""
    __tablename__ = 'plugins'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    name = Column(String(100), nullable=True, doc='name')


    slug = Column(String(100), unique=True, nullable=True, doc='slug')


    version = Column(String(20), nullable=True, doc='version')

    description = Column(String(255), nullable=True, doc='description')

    author = Column(String(100), nullable=True, doc='author')

    author_url = Column(String(255), nullable=True, doc='author_url')

    plugin_url = Column(String(255), nullable=True, doc='plugin_url')

    is_active = Column(Boolean, default=False, doc='is_active')

    is_installed = Column(Boolean, default=True, doc='is_installed')

    settings = Column(Text, nullable=True, doc='settings')

    priority = Column(Integer, default=0, doc='priority')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_plugins_slug', 'slug', unique=True),
        Index('idx_plugins_is_active', 'is_active'),
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
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'author_url': self.author_url,
            'plugin_url': self.plugin_url,
            'is_active': self.is_active,
            'is_installed': self.is_installed,
            'settings': self.settings,
            'priority': self.priority,
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
        return f'<Plugin id={self.id}>'
