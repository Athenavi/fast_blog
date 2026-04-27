"""
SQLAlchemy 模型定义 - MediaFolder
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)

from . import Base  # 使用统一的 Base


class MediaFolder(Base):
    """媒体文件夹模型模型"""
    __tablename__ = 'media_folders'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    name = Column(String(255), nullable=True, doc='name')


    parent_id = Column('parent_id', BigInteger, ForeignKey('media_folders.id'), nullable=True, doc='parent_id')

    user = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user')

    description = Column(String(255), nullable=True, doc='description')

    sort_order = Column(BigInteger, default=0, doc='sort_order')

    is_public = Column(Boolean, default=True, doc='is_public')

    media_count = Column(BigInteger, default=0, doc='media_count')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_media_folders_user_id', 'user'),
        Index('idx_media_folders_parent_id', 'parent_id'),
        Index('idx_media_folders_unique_name', 'user', 'parent_id', 'name', unique=True),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'user': self.user,
            'description': self.description,
            'sort_order': self.sort_order,
            'is_public': self.is_public,
            'media_count': self.media_count,
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
        return f'<MediaFolder id={self.id}>'
