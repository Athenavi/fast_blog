"""
SQLAlchemy 模型定义 - ArticleI18n
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class ArticleI18n(Base):
    """文章国际化模型模型"""
    __tablename__ = 'article_i18n'


    i18n_id = Column(BigInteger, primary_key=True, autoincrement=True, doc='i18n_id')


    article = Column(BigInteger, ForeignKey('articles.id'), nullable=False, doc='article')


    language_id = Column(String(10), nullable=True, doc='language_id')

    title = Column(String(255), nullable=True, doc='title')

    slug = Column(String(255), nullable=True, doc='slug')

    content = Column(Text, nullable=False, doc='content')

    excerpt = Column(String(255), nullable=True, doc='excerpt')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'i18n_id': self.i18n_id,
            'article': self.article,
            'language_id': self.language_id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'excerpt': self.excerpt,
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
        return f'<ArticleI18n id={self.i18n_id}>'
