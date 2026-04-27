"""
SQLAlchemy 模型定义 - ArticleRevision
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)
from sqlalchemy.orm import relationship

from . import Base  # 使用统一的 Base


class ArticleRevision(Base):
    """文章修订历史模型模型"""
    __tablename__ = 'article_revisions'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    article_id = Column(BigInteger, ForeignKey('articles.id'), nullable=False, doc='article_id')


    revision_number = Column(BigInteger, doc='revision_number')


    title = Column(String(255), nullable=True, doc='title')

    excerpt = Column(String(255), nullable=True, doc='excerpt')

    content = Column(Text, nullable=False, doc='content')

    cover_image = Column(String(255), nullable=True, doc='cover_image')

    tags_list = Column(String(255), nullable=True, doc='tags_list')

    category_id = Column(BigInteger, nullable=True, doc='category_id')

    status = Column(BigInteger, default=0, doc='status')

    hidden = Column(Boolean, default=False, doc='hidden')

    is_featured = Column(Boolean, default=False, doc='is_featured')

    is_vip_only = Column(Boolean, default=False, doc='is_vip_only')

    required_vip_level = Column(BigInteger, default=0, doc='required_vip_level')

    author_id = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='author_id')

    change_summary = Column(String(500), nullable=True, doc='change_summary')

    created_at = Column(DateTime, doc='created_at')


    __table_args__ = (

    Index('idx_article_revisions_article_id', 'article_id'),
        Index('idx_article_revisions_number', 'revision_number'),
        Index('idx_article_revisions_created', 'created_at'),
    )

    # 关系定义
    article = relationship('Article', back_populates='revisions',
                           primaryjoin="ArticleRevision.article_id == Article.id")

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'article_id': self.article_id,
            'revision_number': self.revision_number,
            'title': self.title,
            'excerpt': self.excerpt,
            'content': self.content,
            'cover_image': self.cover_image,
            'tags_list': self.tags_list,
            'category_id': self.category_id,
            'status': self.status,
            'hidden': self.hidden,
            'is_featured': self.is_featured,
            'is_vip_only': self.is_vip_only,
            'required_vip_level': self.required_vip_level,
            'author_id': self.author_id,
            'change_summary': self.change_summary,
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
        return f'<ArticleRevision id={self.id}>'
