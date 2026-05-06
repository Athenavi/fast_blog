"""
SQLAlchemy 模型定义 - ShareStat
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-05-06 17:36:26
"""

from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index

from . import Base  # 使用统一的 Base


class ShareStat(Base):
    """分享统计模型模型"""
    __tablename__ = 'share_stats'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    article_id = Column(BigInteger, ForeignKey('articles.id'), nullable=False, doc='article_id')


    platform = Column(String(50), index=True, nullable=True, doc='platform')


    shared_by = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='shared_by')


    ip_address = Column(String(45), nullable=True, doc='ip_address')


    user_agent = Column(String(500), nullable=True, doc='user_agent')


    created_at = Column(DateTime, doc='created_at')

    __table_args__ = (

        Index('idx_share_stats_article_platform', 'article_id', 'platform'),
        Index('idx_share_stats_created', 'created_at'),
        Index('idx_share_stats_article_created', 'article_id', 'created_at'),
    )

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'article_id': self.article_id,
            'platform': self.platform,
            'shared_by': self.shared_by,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
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
        return f'<ShareStat id={self.id}>'
