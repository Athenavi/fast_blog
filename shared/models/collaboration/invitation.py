"""
SQLAlchemy 模型定义 - CollaborationInvite
手写模型（v3 content/collaboration 批次），写法对齐代码生成器产物。

协作邀请用 ``target_type`` + ``target_id`` **泛化**：
  - ``target_type="article"``   → 邀请他人协作编辑某篇文章（v2 的语义，但 v2 把它存在进程内存里）
  - ``target_type="workspace"`` → 邀请他人加入工作区（与 workspace_members 体系一致）

与 v2 的差异（v2 的 ``collaboration_invites.py`` 是**进程内 dict**，重启/多 worker 即丢）：
这里是真表 + 真迁移。
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class CollaborationInvite(Base):
    """协作邀请模型"""
    __tablename__ = 'collaboration_invites'

    __table_args__ = (
        # 命名唯一约束（与最新迁移口径一致：不重复创建同名 Index）
        UniqueConstraint('invite_code', name='idx_collaboration_invites_code'),
        Index('idx_collaboration_invites_target', 'target_type', 'target_id'),
        Index('idx_collaboration_invites_active', 'is_active'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='邀请 ID')

    invite_code = Column(String(64), nullable=False, doc='邀请码（唯一）')

    target_type = Column(String(50), nullable=False, doc='目标类型 (article/workspace)')

    target_id = Column(BigInteger, nullable=False, doc='目标 ID')

    permission = Column(String(20), default='edit', doc='权限 (view/edit)')

    creator_id = Column(BigInteger, ForeignKey('users.id'), doc='创建人')

    expires_at = Column(DateTime, nullable=True, doc='过期时间')

    max_uses = Column(Integer, default=0, doc='最大使用次数 (0 = 不限)')

    use_count = Column(Integer, default=0, doc='已使用次数')

    is_active = Column(Boolean, default=True, doc='是否激活')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'invite_code': self.invite_code,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'permission': self.permission,
            'creator_id': self.creator_id,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'max_uses': self.max_uses,
            'use_count': self.use_count,
            'is_active': self.is_active,
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
        return f'<CollaborationInvite id={self.id}>'
