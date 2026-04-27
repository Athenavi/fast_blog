"""
SQLAlchemy 模型定义 - CommentVote
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float,
                        ForeignKey, Index, Integer, String, Text)

from . import Base  # 使用统一的 Base


class CommentVote(Base):
    """评论投票模型模型"""
    __tablename__ = 'comment_votes'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    comment_id = Column(BigInteger, index=True, doc='comment_id')


    user = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='user')


    vote_type = Column(Integer, doc='vote_type')

    ip_address = Column(String(45), nullable=True, doc='ip_address')

    created_at = Column(DateTime, doc='created_at')


    __table_args__ = (

    Index('idx_comment_votes_comment_user', 'comment_id', 'user', unique=True),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'comment_id': self.comment_id,
            'user': self.user,
            'vote_type': self.vote_type,
            'ip_address': self.ip_address,
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
        return f'<CommentVote id={self.id}>'
