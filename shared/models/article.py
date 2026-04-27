"""
SQLAlchemy 模型定义 - Article
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float,
                        ForeignKey, Index, Integer, String, Text)
from sqlalchemy.orm import relationship

from . import Base  # 使用统一的 Base


class Article(Base):
    """文章模型模型"""
    __tablename__ = 'articles'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    title = Column(String(255), nullable=True, doc='title')


    slug = Column(String(255), nullable=True, doc='slug')


    excerpt = Column(String(255), nullable=True, doc='excerpt')


    cover_image = Column(String(255), nullable=True, doc='cover_image')

    category = Column(BigInteger, ForeignKey('categories.id'), nullable=True, doc='category')

    tags_list = Column(String(255), nullable=True, doc='tags_list')

    views = Column(BigInteger, default=0, doc='views')

    user = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user')

    likes = Column(BigInteger, default=0, doc='likes')

    status = Column(Integer, doc='status')

    hidden = Column(Boolean, default=False, doc='hidden')

    is_featured = Column(Boolean, default=False, doc='is_featured')

    is_vip_only = Column(Boolean, default=False, doc='is_vip_only')

    required_vip_level = Column(Integer, default=0, doc='required_vip_level')

    article_ad = Column(String(255), nullable=True, doc='article_ad')

    scheduled_publish_at = Column(DateTime, nullable=True, doc='scheduled_publish_at')

    post_type = Column(String(50), index=True, default='article', doc='post_type')

    is_sticky = Column(Boolean, default=False, doc='is_sticky')

    sticky_until = Column(DateTime, nullable=True, doc='sticky_until')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_articles_status', 'status'),
        Index('idx_articles_category', 'category'),
        Index('idx_articles_user_id', 'user'),
        Index('idx_articles_created_at', 'created_at'),
        Index('idx_articles_scheduled_publish', 'scheduled_publish_at'),
        Index('idx_articles_status_created', 'status', 'created_at'),
        Index('idx_articles_is_sticky', 'is_sticky'),
        Index('idx_articles_sticky_until', 'sticky_until'),
    )

    # 关系定义
    revisions = relationship('ArticleRevision', back_populates='article',
                             primaryjoin="Article.id == ArticleRevision.article_id")
    seo_data = relationship('ArticleSEO', back_populates='article', primaryjoin="Article.id == ArticleSEO.article_id")

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'excerpt': self.excerpt,
            'cover_image': self.cover_image,
            'category': self.category,
            'tags_list': self.tags_list,
            'views': self.views,
            'user': self.user,
            'likes': self.likes,
            'status': self.status,
            'hidden': self.hidden,
            'is_featured': self.is_featured,
            'is_vip_only': self.is_vip_only,
            'required_vip_level': self.required_vip_level,
            'article_ad': self.article_ad,
            'scheduled_publish_at': self.scheduled_publish_at.isoformat() if self.scheduled_publish_at else None,
            'post_type': self.post_type,
            'is_sticky': self.is_sticky,
            'sticky_until': self.sticky_until.isoformat() if self.sticky_until else None,
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
        return f'<Article id={self.id}>'
