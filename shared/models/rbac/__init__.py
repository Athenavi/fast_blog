"""
rbac 子模块 - 模型定义
由代码生成器自动生成 - 请勿手动修改
"""
from .capability import Capability
from .permission_audit_log import PermissionAuditLog
from .role import Role
from .role_capability import RoleCapability
from .user_role import UserRole

__all__ = ['Capability', 'PermissionAuditLog', 'Role', 'RoleCapability', 'UserRole']
