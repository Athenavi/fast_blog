"""
SQLAlchemy 模型定义 - Notification
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class Notification(Base):
    """通知模型模型"""
    __tablename__ = 'notifications'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    recipient = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='recipient')

    type = Column(String(100), nullable=True, doc='type')

    title = Column(String(200), nullable=True, doc='title')

    message = Column(String(255), nullable=True, doc='message')

    is_read = Column(Boolean, default=False, doc='is_read')

    read_at = Column(DateTime, nullable=True, doc='read_at')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'recipient': self.recipient,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
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
        return f'<Notification id={self.id}>'
