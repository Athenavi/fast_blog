"""
SQLAlchemy 模型定义 - ChatMessage
手写模型（2026-09-20 批次 17），写法对齐代码生成器产物。

**群聊消息**。表 `chat_groups` / `chat_group_members` 早在批次 4 就存在，但当时 `chat/group`
只有 CRUD：既没有消息，也没有实时通道 —— 本表补上消息侧（实时广播走 Redis，
见 `src/api/v3/modules/chat/message/service.py`）。

撤回用**软删除**（`is_deleted`），保留行以便前端显示"该消息已撤回"，
同时避免消息序号跳变。
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, String, Text

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class ChatMessage(Base):
    """群聊消息模型"""
    __tablename__ = 'chat_messages'

    __table_args__ = (
        Index('idx_chat_messages_group_created', 'group', 'created_at'),
        Index('idx_chat_messages_user_created', 'user', 'created_at'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='消息 ID')

    group = Column(
        BigInteger,
        ForeignKey('chat_groups.id', ondelete='CASCADE'),
        nullable=False,
        doc='群聊 ID（群解散时消息一并删除）',
    )

    user = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='发送者 ID')

    content = Column(Text, nullable=False, doc='消息内容')

    message_type = Column(String(50), default='text', doc='消息类型（text/image/file/system）')

    attachment_url = Column(String(500), nullable=True, doc='附件 URL（图片/文件）')

    parent_message = Column(
        BigInteger,
        ForeignKey('chat_messages.id', ondelete='SET NULL'),
        nullable=True,
        doc='引用的消息 ID（回复；被引用消息删除时置空）',
    )

    is_deleted = Column(Boolean, default=False, doc='是否已撤回（软删除）')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'group': self.group,
            'user': self.user,
            'content': self.content,
            'message_type': self.message_type,
            'attachment_url': self.attachment_url,
            'parent_message': self.parent_message,
            'is_deleted': bool(self.is_deleted),
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
        return f'<ChatMessage id={self.id} group={self.group}>'
