"""
SQLAlchemy 模型定义 - PrivateMessage
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-05-08 10:43:26
"""


from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, ForeignKey

from . import Base  # 使用统一的 Base

from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, ForeignKey, Index

class PrivateMessage(Base):
    """站内私信模型模型"""
    __tablename__ = 'private_messages'



    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    sender = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='sender')


    recipient = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='recipient')


    content = Column(Text, nullable=False, doc='content')


    message_type = Column(String(50), default='text', doc='message_type')


    attachment_url = Column(String(500), nullable=True, doc='attachment_url')


    is_read = Column(Boolean, default=False, doc='is_read')


    read_at = Column(DateTime, nullable=True, doc='read_at')


    is_deleted_by_sender = Column(Boolean, default=False, doc='is_deleted_by_sender')

    is_deleted_by_recipient = Column(Boolean, default=False, doc='is_deleted_by_recipient')

    parent_message = Column('parent_message', BigInteger, ForeignKey('private_messages.id'), nullable=True,
                            doc='parent_message')


    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')

    __table_args__ = (

        Index('idx_private_messages_sender', 'sender'),
        Index('idx_private_messages_recipient', 'recipient'),
        Index('idx_private_messages_created', 'created_at'),
        Index('idx_private_messages_conversation', 'sender', 'recipient'),
        Index('idx_private_messages_is_read', 'is_read'),

    )

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'sender': self.sender,
            'recipient': self.recipient,
            'content': self.content,
            'message_type': self.message_type,
            'attachment_url': self.attachment_url,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'is_deleted_by_sender': self.is_deleted_by_sender,
            'is_deleted_by_recipient': self.is_deleted_by_recipient,
            'parent_message': self.parent_message,
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
        return f'<PrivateMessage id={self.id}>'
