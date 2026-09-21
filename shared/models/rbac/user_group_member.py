"""
SQLAlchemy 模型定义 - UserGroupMember
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-09-18 15:22:48
"""

from sqlalchemy import Column, BigInteger, DateTime, ForeignKey, Index, UniqueConstraint

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class UserGroupMember(Base):
    """用户-权限组关联模型（一人多组）模型"""
    __tablename__ = 'user_group_members'

    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', name='idx_user_group_members_unique'),
        Index('idx_user_group_members_user', 'user_id'),
        Index('idx_user_group_members_group', 'group_id'),
        # 不要加同名 Index(..., unique=True)：UniqueConstraint 已创建同名唯一索引（批次 21 实测会冲突）
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='关联 ID')

    user_id = Column(BigInteger, ForeignKey('users.id'), doc='用户 ID')

    group_id = Column(BigInteger, ForeignKey('permission_groups.id'), doc='权限组 ID')

    created_at = Column(DateTime, doc='加入时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'group_id': self.group_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<UserGroupMember id={self.id}>'
