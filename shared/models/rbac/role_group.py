"""
SQLAlchemy 模型定义 - RoleGroup
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-09-18 15:22:48
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class RoleGroup(Base):
    """角色-权限组关联模型（data_scope=5 自定义范围时使用）模型"""
    __tablename__ = 'role_groups'

    __table_args__ = (
        UniqueConstraint('role_id', 'group_id', name='idx_role_groups_unique'),
        Index('idx_role_groups_role', 'role_id'),
        Index('idx_role_groups_group', 'group_id'),
        Index('idx_role_groups_unique', 'role_id', 'group_id', unique=True),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='关联 ID')

    role_id = Column(BigInteger, ForeignKey('roles.id'), doc='角色 ID')

    group_id = Column(BigInteger, ForeignKey('permission_groups.id'), doc='权限组 ID')

    created_at = Column(DateTime, doc='创建时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'role_id': self.role_id,
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
        return f'<RoleGroup id={self.id}>'
