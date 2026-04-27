"""
SQLAlchemy 模型定义 - Media
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class Media(Base):
    """媒体文件模型模型"""
    __tablename__ = 'media'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    user = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user')

    hash = Column(String(64), nullable=True, doc='hash')

    filename = Column(String(255), nullable=True, doc='filename')

    original_filename = Column(String(255), nullable=True, doc='original_filename')

    file_path = Column(String(500), nullable=True, doc='file_path')

    file_url = Column(String(500), nullable=True, doc='file_url')

    file_size = Column(BigInteger, default=0, doc='file_size')

    file_type = Column(String(255), default='other', doc='file_type')

    mime_type = Column(String(255), nullable=True, doc='mime_type')

    width = Column(BigInteger, nullable=True, doc='width')

    height = Column(BigInteger, nullable=True, doc='height')

    duration = Column(BigInteger, nullable=True, doc='duration')

    thumbnail_path = Column(String(255), nullable=True, doc='thumbnail_path')

    thumbnail_url = Column(String(255), nullable=True, doc='thumbnail_url')

    description = Column(String(255), nullable=True, doc='description')

    alt_text = Column(String(255), nullable=True, doc='alt_text')

    is_public = Column(Boolean, default=True, doc='is_public')

    download_count = Column(BigInteger, default=0, doc='download_count')

    category = Column(String(100), nullable=True, doc='category')

    tags = Column(String(500), nullable=True, doc='tags')

    folder_id = Column(BigInteger, ForeignKey('media_folders.id'), nullable=True, doc='folder_id')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user': self.user,
            'hash': self.hash,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_path': self.file_path,
            'file_url': self.file_url,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'thumbnail_path': self.thumbnail_path,
            'thumbnail_url': self.thumbnail_url,
            'description': self.description,
            'alt_text': self.alt_text,
            'is_public': self.is_public,
            'download_count': self.download_count,
            'category': self.category,
            'tags': self.tags,
            'folder_id': self.folder_id,
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
        return f'<Media id={self.id}>'
