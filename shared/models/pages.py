"""
SQLAlchemy 模型定义 - Pages
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, Index,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class Pages(Base):
    """页面模型模型"""
    __tablename__ = 'pages'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    title = Column(String(255), nullable=True, doc='title')


    slug = Column(String(255), nullable=True, doc='slug')


    content = Column(String(255), nullable=True, doc='content')

    excerpt = Column(String(255), nullable=True, doc='excerpt')

    template = Column(String(255), nullable=True, doc='template')

    status = Column(BigInteger, default=0, doc='status')

    author_id = Column(BigInteger, nullable=True, doc='author_id')

    parent_id = Column(BigInteger, nullable=True, doc='parent_id')

    order_index = Column(Integer, default=0, doc='order_index')

    meta_title = Column(String(255), nullable=True, doc='meta_title')

    meta_description = Column(String(255), nullable=True, doc='meta_description')

    meta_keywords = Column(String(255), nullable=True, doc='meta_keywords')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')

    published_at = Column(DateTime, nullable=True, doc='published_at')


    __table_args__ = (

    Index('idx_pages_slug', 'slug', unique=True),
        Index('idx_pages_status', 'status'),
        Index('idx_pages_author_id', 'author_id'),
        Index('idx_pages_parent_id', 'parent_id'),
        Index('idx_pages_order', 'order_index'),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'excerpt': self.excerpt,
            'template': self.template,
            'status': self.status,
            'author_id': self.author_id,
            'parent_id': self.parent_id,
            'order_index': self.order_index,
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'meta_keywords': self.meta_keywords,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Pages id={self.id}>'
