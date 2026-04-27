"""
SQLAlchemy 模型定义 - ArticleContent
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class ArticleContent(Base):
    """文章内容模型模型"""
    __tablename__ = 'article_content'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    article = Column(BigInteger, ForeignKey('articles.id'), nullable=False, doc='article')


    passwd = Column(String(255), nullable=True, doc='passwd')

    content = Column(Text, nullable=False, doc='content')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')

    language_code = Column(String(255), default='zh-CN', doc='language_code')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'article': self.article,
            'passwd': self.passwd,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
                'language_code': self.language_code,
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<ArticleContent id={self.id}>'
