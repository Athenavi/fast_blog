import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from . import Base  # 使用统一的Base


class UploadTask(Base):
    """上传任务表"""
    __tablename__ = 'upload_tasks'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    total_size = Column(BigInteger, nullable=False)  # 文件总大小
    total_chunks = Column(Integer, nullable=False)  # 总分块数
    uploaded_chunks = Column(Integer, default=0)  # 已上传分块数
    file_hash = Column(String(64))  # 文件哈希（用于秒传）
    status = Column(String(20), default='initialized')  # initialized | uploading | completed | cancelled
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())

    user = relationship('User', backref='upload_tasks')
    chunks = relationship('UploadChunk', back_populates='task', lazy=True, cascade='all, delete-orphan')


class UploadChunk(Base):
    """上传分块表"""
    __tablename__ = 'upload_chunks'

    id = Column(Integer, primary_key=True)
    upload_id = Column(String(36), ForeignKey('upload_tasks.id'), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # 分块索引
    chunk_hash = Column(String(64), nullable=False)  # 分块哈希
    chunk_size = Column(Integer, nullable=False)  # 分块大小
    chunk_path = Column(String(500), nullable=False)  # 分块存储路径
    created_at = Column(DateTime, default=lambda: datetime.now())

    # 关系定义
    task = relationship('UploadTask', back_populates='chunks')

    # 唯一约束，确保同一上传任务的每个分块索引唯一
    __table_args__ = (
        UniqueConstraint('upload_id', 'chunk_index', name='uix_upload_chunk'),
    )