"""
SQLAlchemy 模型定义 - PermissionGroup
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-09-18 15:22:48
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

# 提前导入关联表所在模块，确保 secondary 字符串（user_group_members / role_groups）可被解析
import shared.models.rbac.role_group  # noqa: F401
import shared.models.rbac.user_group_member  # noqa: F401
from shared.models import Base  # 使用统一的 Base（跨子包引用）


class PermissionGroup(Base):
    """权限用户组模型（替代官方的“部门”，承载数据权限范围）模型"""
    __tablename__ = 'permission_groups'

    __table_args__ = (
        UniqueConstraint('code', name='idx_permission_groups_code'),
        Index('idx_permission_groups_code', 'code', unique=True),
        Index('idx_permission_groups_parent', 'parent_id'),
        Index('idx_permission_groups_active', 'is_active'),
        Index('idx_permission_groups_sort', 'sort_order'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='权限组 ID')

    name = Column(String(100), nullable=True, doc='权限组名称')

    code = Column(String(100), unique=True, nullable=True, doc='权限组标识（唯一）')

    description = Column(String(255), nullable=True, doc='权限组描述')

    parent_id = Column(BigInteger, ForeignKey('permission_groups.id'), nullable=True,
                       doc='父权限组 ID（树形，用于“本组及以下”数据范围）')

    sort_order = Column(BigInteger, default=0, doc='显示排序')

    owner_id = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='组长用户 ID')

    is_active = Column(Boolean, default=True, doc='是否激活')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    # 关系定义
    users = relationship('User', secondary='user_group_members', back_populates='permission_groups',
                         primaryjoin="PermissionGroup.id == user_group_members.c.group_id",
                         secondaryjoin="user_group_members.c.user_id == User.id")
    roles = relationship('Role', secondary='role_groups', back_populates='groups',
                         primaryjoin="PermissionGroup.id == role_groups.c.group_id",
                         secondaryjoin="role_groups.c.role_id == Role.id")

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'parent_id': self.parent_id,
            'sort_order': self.sort_order,
            'owner_id': self.owner_id,
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
        return f'<PermissionGroup id={self.id}>'
