"""
SQLAlchemy 模型定义 - TeamComment
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-06-13 22:56:46
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Index

from shared.models import Base  # 使用统一的 Base（跨子包引用）



class TeamComment(Base):
    """团队评论模型（支持协作、@提及、已解决状态）模型"""
    __tablename__ = 'team_comments'


    __table_args__ = (
        Index('idx_team_comments_content', 'content_type', 'content_id'),
        Index('idx_team_comments_author', 'author_id'),
        Index('idx_team_comments_parent', 'parent_id'),
        Index('idx_team_comments_resolved', 'is_resolved'),
    )


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='团队评论 ID')

    content_type = Column(String(50), nullable=True, doc='内容类型（article, page, block 等）')

    content_id = Column(BigInteger, doc='内容 ID')


    author_id = Column(BigInteger, ForeignKey('users.id'), doc='作者 ID')


    parent_id = Column(BigInteger, ForeignKey('team_comments.id'), nullable=True, doc='父评论 ID（用于回复）')


    text = Column(Text, nullable=False, doc='评论内容')


    mentions = Column(String(500), nullable=True, doc='@提及的用户 ID 列表（JSON 数组）')

    is_resolved = Column(Boolean, default=False, doc='是否已解决')


    resolved_by = Column(BigInteger, nullable=True, doc='解决者 ID')


    resolved_at = Column(DateTime, nullable=True, doc='解决时间')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, nullable=True, doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'content_type': self.content_type,
            'content_id': self.content_id,
            'author_id': self.author_id,
            'parent_id': self.parent_id,
            'text': self.text,
            'mentions': self.mentions,
            'is_resolved': self.is_resolved,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
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
        return f'<TeamComment id={self.id}>'


