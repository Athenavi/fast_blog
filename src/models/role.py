from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from . import Base  # 使用统一的Base


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=False)

    # 通过中间表连接到用户
    users = relationship('User', secondary='user_roles', back_populates='roles', overlaps="user_roles,role_permissions,permissions,users")
    permissions = relationship('Permission', secondary='role_permissions', back_populates='roles', overlaps="role_permissions,user_roles,role_permissions")
    user_roles = relationship('UserRole', back_populates='role', overlaps="users,permissions,role_permissions,permissions,users")
    role_permissions = relationship('RolePermission', back_populates='role', overlaps="permissions,users,user_roles,permission,role")


class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=False)

    # 关系定义 - 使用关联表模型
    roles = relationship('Role', secondary='role_permissions', back_populates='permissions', overlaps="role_permissions,user_roles,role,role_permissions")
    role_permissions = relationship('RolePermission', back_populates='permission', overlaps="roles,user_roles,role,permission")


class UserRole(Base):
    __tablename__ = 'user_roles'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)

    # 建立与User和Role的外键关系，方便查询
    user = relationship('User', back_populates='user_roles', overlaps="roles,permissions,user_roles,role_permissions,users,role_permissions")
    role = relationship('Role', back_populates='user_roles', overlaps="users,permissions,role_permissions,roles,permissions")


class RolePermission(Base):
    __tablename__ = 'role_permissions'
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(Integer, ForeignKey('permissions.id'), primary_key=True)

    # 建立与Role和Permission的外键关系，方便查询
    role = relationship('Role', back_populates='role_permissions', overlaps="permissions,users,user_roles,roles,permission")
    permission = relationship('Permission', back_populates='role_permissions', overlaps="roles,users,user_roles,role,permissions")