"""
SQLAlchemy 模型定义 - UploadTask
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


import uuid
from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Integer, String,
                        Text)

from . import Base  # 使用统一的 Base


class UploadTask(Base):
    """上传任务模型模型"""
    __tablename__ = 'upload_tasks'


    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='id')


    user_id = Column(BigInteger, doc='user_id')


    filename = Column(String(255), nullable=True, doc='filename')


    total_size = Column(BigInteger, doc='total_size')

    total_chunks = Column(BigInteger, doc='total_chunks')

    uploaded_chunks = Column(BigInteger, default=0, doc='uploaded_chunks')

    file_hash = Column(String(64), nullable=True, doc='file_hash')

    status = Column(String(255), default='initialized', doc='status')

    created_at = Column(DateTime, default=datetime.utcnow, doc='created_at')

    updated_at = Column(DateTime, default=datetime.utcnow, doc='updated_at')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'total_size': self.total_size,
            'total_chunks': self.total_chunks,
            'uploaded_chunks': self.uploaded_chunks,
            'file_hash': self.file_hash,
            'status': self.status,
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
        return f'<UploadTask id={self.id}>'
