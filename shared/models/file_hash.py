"""
SQLAlchemy 模型定义 - FileHash
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Integer, String,
                        Text)

from . import Base  # 使用统一的 Base


class FileHash(Base):
    """文件哈希模型模型"""
    __tablename__ = 'file_hashs'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    hash = Column(String(64), nullable=True, doc='hash')


    filename = Column(String(255), nullable=True, doc='filename')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')

    reference_count = Column(BigInteger, default=1, doc='reference_count')

    file_size = Column(BigInteger, doc='file_size')

    mime_type = Column(String(100), nullable=True, doc='mime_type')

    storage_path = Column(String(512), nullable=True, doc='storage_path')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'hash': self.hash,
            'filename': self.filename,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'reference_count': self.reference_count,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'storage_path': self.storage_path,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<FileHash id={self.id}>'
