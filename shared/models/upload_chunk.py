"""
SQLAlchemy 模型定义 - UploadChunk
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Integer, String,
                        Text)

from . import Base  # 使用统一的 Base


class UploadChunk(Base):
    """上传分块模型模型"""
    __tablename__ = 'upload_chunks'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    upload_id = Column(String(36), nullable=True, doc='upload_id')


    chunk_index = Column(BigInteger, doc='chunk_index')

    chunk_hash = Column(String(64), nullable=True, doc='chunk_hash')

    chunk_size = Column(BigInteger, doc='chunk_size')

    chunk_path = Column(String(500), nullable=True, doc='chunk_path')

    created_at = Column(DateTime, default=datetime.utcnow, doc='created_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'upload_id': self.upload_id,
            'chunk_index': self.chunk_index,
            'chunk_hash': self.chunk_hash,
            'chunk_size': self.chunk_size,
            'chunk_path': self.chunk_path,
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
        return f'<UploadChunk id={self.id}>'
