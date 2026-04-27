"""
SQLAlchemy 模型定义 - Comment
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, Numeric, String, Text)

from . import Base  # 使用统一的 Base


class Comment(Base):
    """评论模型模型"""
    __tablename__ = 'comments'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    article_id = Column(BigInteger, ForeignKey('articles.id'), nullable=False, doc='article_id')


    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='user_id')

    parent_id = Column('parent_id', BigInteger, ForeignKey('comments.id'), nullable=True, doc='parent_id')

    content = Column(Text, nullable=False, doc='content')

    author_name = Column(String(100), nullable=True, doc='author_name')

    author_email = Column(String(255), nullable=True, doc='author_email')

    author_url = Column(String(500), nullable=True, doc='author_url')

    author_ip = Column(String(45), nullable=True, doc='author_ip')

    user_agent = Column(String(500), nullable=True, doc='user_agent')

    is_approved = Column(Boolean, default=True, doc='is_approved')

    likes = Column(BigInteger, default=0, doc='likes')

    spam_score = Column(Numeric(10, 2), nullable=True, doc='spam_score')

    spam_reasons = Column(String(255), nullable=True, doc='spam_reasons')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_comments_article_id', 'article_id'),
        Index('idx_comments_user_id', 'user_id'),
        Index('idx_comments_parent_id', 'parent_id'),
        Index('idx_comments_is_approved', 'is_approved'),
        Index('idx_comments_created_at', 'created_at'),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'article_id': self.article_id,
            'user_id': self.user_id,
            'parent_id': self.parent_id,
            'content': self.content,
            'author_name': self.author_name,
            'author_email': self.author_email,
            'author_url': self.author_url,
            'user_agent': self.user_agent,
            'is_approved': self.is_approved,
            'likes': self.likes,
            'spam_score': self.spam_score,
            'spam_reasons': self.spam_reasons,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
                'author_ip': self.author_ip,
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Comment id={self.id}>'
