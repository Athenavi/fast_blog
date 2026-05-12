"""
细粒度权限服务
提供自定义角色、权限控制、权限继承和权限审计功能
"""
import json
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from shared.models.permission import Permission
from shared.models.role import Role
from shared.models.permission_audit_log import PermissionAuditLog

logger = logging.getLogger(__name__)




class RBACService:
    """
    基于角色的访问控制服务
    
    功能:
    1. 细粒度权限控制
    2. 自定义角色管理
    3. 权限继承
    4. 权限审计
    """

    def __init__(self):
        # 预定义的系统角色
        self.system_roles = {
            'super_admin': {
                'name': '超级管理员',
                'description': '拥有所有权限',
                'permissions': ['*']  # 所有权限
            },
            'admin': {
                'name': '管理员',
                'description': '网站管理员',
                'permissions': [
                    'article:create', 'article:read', 'article:update', 'article:delete',
                    'user:read', 'user:update',
                    'category:create', 'category:read', 'category:update', 'category:delete',
                    'media:create', 'media:read', 'media:delete',
                    'comment:read', 'comment:delete',
                    'settings:read', 'settings:update',
                ]
            },
            'editor': {
                'name': '编辑',
                'description': '内容编辑者',
                'permissions': [
                    'article:create', 'article:read', 'article:update',
                    'media:create', 'media:read',
                    'category:read',
                    'comment:read',
                ]
            },
            'author': {
                'name': '作者',
                'description': '文章作者',
                'permissions': [
                    'article:create', 'article:read', 'article:update',
                    'media:create', 'media:read',
                ]
            },
            'contributor': {
                'name': '贡献者',
                'description': '内容贡献者',
                'permissions': [
                    'article:create', 'article:read',
                    'media:create', 'media:read',
                ]
            },
            'subscriber': {
                'name': '订阅者',
                'description': '普通用户',
                'permissions': [
                    'article:read',
                    'comment:create', 'comment:read',
                ]
            },
        }

    async def initialize_system_roles(self, db):
        """初始化系统角色和权限"""
        from sqlalchemy import select

        # 创建基础权限
        basic_permissions = [
            # 文章权限
            ('article:create', '创建文章', 'article', 'create'),
            ('article:read', '查看文章', 'article', 'read'),
            ('article:update', '更新文章', 'article', 'update'),
            ('article:delete', '删除文章', 'article', 'delete'),
            ('article:publish', '发布文章', 'article', 'publish'),

            # 用户权限
            ('user:create', '创建用户', 'user', 'create'),
            ('user:read', '查看用户', 'user', 'read'),
            ('user:update', '更新用户', 'user', 'update'),
            ('user:delete', '删除用户', 'user', 'delete'),

            # 分类权限
            ('category:create', '创建分类', 'category', 'create'),
            ('category:read', '查看分类', 'category', 'read'),
            ('category:update', '更新分类', 'category', 'update'),
            ('category:delete', '删除分类', 'category', 'delete'),

            # 媒体权限
            ('media:create', '上传媒体', 'media', 'create'),
            ('media:read', '查看媒体', 'media', 'read'),
            ('media:update', '更新媒体', 'media', 'update'),
            ('media:delete', '删除媒体', 'media', 'delete'),

            # 评论权限
            ('comment:create', '发表评论', 'comment', 'create'),
            ('comment:read', '查看评论', 'comment', 'read'),
            ('comment:update', '更新评论', 'comment', 'update'),
            ('comment:delete', '删除评论', 'comment', 'delete'),
            ('comment:approve', '审核评论', 'comment', 'approve'),

            # 设置权限
            ('settings:read', '查看设置', 'settings', 'read'),
            ('settings:update', '更新设置', 'settings', 'update'),

            # 插件权限
            ('plugin:install', '安装插件', 'plugin', 'install'),
            ('plugin:activate', '激活插件', 'plugin', 'activate'),
            ('plugin:configure', '配置插件', 'plugin', 'configure'),

            # 主题权限
            ('theme:install', '安装主题', 'theme', 'install'),
            ('theme:activate', '激活主题', 'theme', 'activate'),
            ('theme:customize', '自定义主题', 'theme', 'customize'),
        ]

        for code, desc, resource_type, action in basic_permissions:
            stmt = select(Permission).where(Permission.code == code)
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                perm = Permission(
                    name=desc,
                    code=code,
                    description=desc,
                    resource_type=resource_type,
                    action=action
                )
                db.add(perm)

        await db.commit()

        # 创建系统角色
        for slug, role_data in self.system_roles.items():
            stmt = select(Role).where(Role.slug == slug)
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                role = Role(
                    name=role_data['name'],
                    slug=slug,
                    description=role_data['description'],
                    is_system=True
                )
                db.add(role)
                await db.flush()

                # 分配权限
                if '*' in role_data['permissions']:
                    # 超级管理员：获取所有权限
                    all_perms_stmt = select(Permission)
                    all_perms_result = await db.execute(all_perms_stmt)
                    all_perms = all_perms_result.scalars().all()
                    role.permissions = list(all_perms)
                else:
                    # 其他角色：获取指定权限
                    for perm_code in role_data['permissions']:
                        perm_stmt = select(Permission).where(Permission.code == perm_code)
                        perm_result = await db.execute(perm_stmt)
                        perm = perm_result.scalar_one_or_none()
                        if perm:
                            role.permissions.append(perm)

        await db.commit()
        logger.info("System roles and permissions initialized")

    async def create_custom_role(self, db, name: str, slug: str, description: str = None,
                                 permission_codes: List[str] = None,
                                 parent_role_id: int = None) -> Role:
        """
        创建自定义角色
        
        Args:
            db: 数据库会话
            name: 角色名称
            slug: 角色标识
            description: 描述
            permission_codes: 权限代码列表
            parent_role_id: 父角色ID（用于继承）
            
        Returns:
            创建的角色
        """
        from sqlalchemy import select

        # 检查slug是否已存在
        stmt = select(Role).where(Role.slug == slug)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError(f"Role with slug '{slug}' already exists")

        # 创建角色
        role = Role(
            name=name,
            slug=slug,
            description=description,
            is_system=False,
            parent_id=parent_role_id
        )

        db.add(role)
        await db.flush()

        # 如果指定了父角色，继承其权限
        if parent_role_id:
            parent_stmt = select(Role).where(Role.id == parent_role_id)
            parent_result = await db.execute(parent_stmt)
            parent_role = parent_result.scalar_one_or_none()

            if parent_role:
                role.permissions = list(parent_role.permissions)

        # 添加指定的权限
        if permission_codes:
            for code in permission_codes:
                perm_stmt = select(Permission).where(Permission.code == code)
                perm_result = await db.execute(perm_stmt)
                perm = perm_result.scalar_one_or_none()
                if perm:
                    role.permissions.append(perm)

        await db.commit()
        await db.refresh(role)

        logger.info(f"Custom role created: {slug}")
        return role

    async def assign_role_to_user(self, db, user_id: int, role_id: int):
        """
        为用户分配角色
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            role_id: 角色ID
        """
        from shared.models.user import User

        user = await db.get(User, user_id)
        role = await db.get(Role, role_id)

        if not user or not role:
            raise ValueError("User or role not found")

        if role not in user.roles:
            user.roles.append(role)
            await db.commit()

            logger.info(f"Role {role.slug} assigned to user {user_id}")

    async def remove_role_from_user(self, db, user_id: int, role_id: int):
        """
        从用户移除角色
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            role_id: 角色ID
        """
        from shared.models.user import User

        user = await db.get(User, user_id)
        role = await db.get(Role, role_id)

        if not user or not role:
            raise ValueError("User or role not found")

        if role in user.roles:
            user.roles.remove(role)
            await db.commit()

            logger.info(f"Role {role.slug} removed from user {user_id}")

    async def check_permission(self, db, user_id: int, permission_code: str) -> bool:
        """
        检查用户是否有指定权限
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            permission_code: 权限代码
            
        Returns:
            是否有权限
        """
        from shared.models.user import User
        from sqlalchemy import select

        user = await db.get(User, user_id)
        if not user:
            return False

        # 检查用户的所有角色
        for role in user.roles:
            if not role.is_active:
                continue

            # 检查角色是否有该权限
            for perm in role.permissions:
                if perm.code == permission_code or perm.code == '*':
                    return True

            # 检查父角色（权限继承）
            if role.parent:
                parent_role = await db.get(Role, role.parent_id)
                if parent_role and parent_role.is_active:
                    for perm in parent_role.permissions:
                        if perm.code == permission_code or perm.code == '*':
                            return True

        return False

    async def get_user_permissions(self, db, user_id: int) -> List[str]:
        """
        获取用户的所有权限
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            权限代码列表
        """
        from shared.models.user import User

        user = await db.get(User, user_id)
        if not user:
            return []

        permissions = set()

        for role in user.roles:
            if not role.is_active:
                continue

            for perm in role.permissions:
                permissions.add(perm.code)

            # 继承父角色权限
            if role.parent_id:
                parent_role = await db.get(Role, role.parent_id)
                if parent_role and parent_role.is_active:
                    for perm in parent_role.permissions:
                        permissions.add(perm.code)

        return list(permissions)

    async def add_permission_to_role(self, db, role_id: int, permission_code: str):
        """
        为角色添加权限
        
        Args:
            db: 数据库会话
            role_id: 角色ID
            permission_code: 权限代码
        """
        from sqlalchemy import select

        role = await db.get(Role, role_id)
        if not role:
            raise ValueError("Role not found")

        if role.is_system:
            raise ValueError("Cannot modify system role permissions")

        perm_stmt = select(Permission).where(Permission.code == permission_code)
        perm_result = await db.execute(perm_stmt)
        perm = perm_result.scalar_one_or_none()

        if not perm:
            raise ValueError(f"Permission '{permission_code}' not found")

        if perm not in role.permissions:
            role.permissions.append(perm)
            await db.commit()

            logger.info(f"Permission {permission_code} added to role {role.slug}")

    async def remove_permission_from_role(self, db, role_id: int, permission_code: str):
        """
        从角色移除权限
        
        Args:
            db: 数据库会话
            role_id: 角色ID
            permission_code: 权限代码
        """
        from sqlalchemy import select

        role = await db.get(Role, role_id)
        if not role:
            raise ValueError("Role not found")

        if role.is_system:
            raise ValueError("Cannot modify system role permissions")

        perm_stmt = select(Permission).where(Permission.code == permission_code)
        perm_result = await db.execute(perm_stmt)
        perm = perm_result.scalar_one_or_none()

        if perm and perm in role.permissions:
            role.permissions.remove(perm)
            await db.commit()

            logger.info(f"Permission {permission_code} removed from role {role.slug}")

    async def log_permission_change(self, db, user_id: int, action: str,
                                    resource_type: str, resource_id: int,
                                    details: Dict = None, ip_address: str = None):
        """
        记录权限变更审计日志
        
        Args:
            db: 数据库会话
            user_id: 操作用户ID
            action: 操作类型
            resource_type: 资源类型
            resource_id: 资源ID
            details: 详细信息
            ip_address: IP地址
        """
        import json

        audit_log = PermissionAuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details, ensure_ascii=False) if details else None,
            ip_address=ip_address
        )

        db.add(audit_log)
        await db.commit()


# 全局实例
rbac_service = RBACService()
