"""
SQLAlchemy 模型定义 - ArticleI18n
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-05-21 08:51:05
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey

from . import Base  # 使用统一的 Base


class ArticleI18n(Base):
    """文章国际化模型模型"""
    __tablename__ = 'article_i18n'




    i18n_id = Column(BigInteger, primary_key=True, autoincrement=True, doc='国际化 ID')

    article = Column(BigInteger, ForeignKey('articles.id'), doc='文章')


    language_id = Column(String(10), nullable=True, doc='语言 ID')

    title = Column(String(255), nullable=True, doc='标题')

    slug = Column(String(255), nullable=True, doc='文章 slug')

    content = Column(Text, nullable=False, doc='文章内容')


    excerpt = Column(String(255), nullable=True, doc='摘要')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')


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

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<ArticleI18n i18n_id={self.i18n_id}>'


