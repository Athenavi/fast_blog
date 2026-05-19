"""
角色权限管理 API
提供细粒度权限控制、自定义角色、权限继承和审计功能
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import PermissionAuditLog, Role
from shared.services.security.rbac_service import rbac_service
from src.api.v1.core.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from src.utils.security.security import Permission

router = APIRouter(tags=["rbac"])


# ==================== 角色管理 ====================

@router.post("/roles", summary="创建自定义角色")
async def create_role(
        name: str = Body(..., description="角色名称"),
        slug: str = Body(..., description="角色标识"),
        description: Optional[str] = Body(None, description="描述"),
        permission_codes: Optional[List[str]] = Body(None, description="权限代码列表"),
        parent_role_id: Optional[int] = Body(None, description="父角色ID（用于继承）"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建自定义角色
    
    Args:
        name: 角色名称
        slug: 角色标识
        description: 描述
        permission_codes: 权限代码列表
        parent_role_id: 父角色ID
        
    Returns:
        创建的角色
    """
    try:
        # 检查权限（需要admin权限）
        has_permission = await rbac_service.check_permission(db, current_user.id, 'user:update')
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        role = await rbac_service.create_custom_role(
            db=db,
            name=name,
            slug=slug,
            description=description,
            permission_codes=permission_codes,
            parent_role_id=parent_role_id
        )

        # 记录审计日志
        await rbac_service.log_permission_change(
            db=db,
            user_id=current_user.id,
            action='create_role',
            resource_type='role',
            resource_id=role.id,
            details={'name': name, 'slug': slug}
        )

        return ApiResponse(
            success=True,
            data={
                'id': role.id,
                'name': role.name,
                'slug': role.slug,
                'description': role.description,
                'is_system': role.is_system,
                'parent_id': role.parent_id,
                'permission_count': len(role.permissions),
            },
            message="Role created successfully"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/roles", summary="获取角色列表")
async def get_roles(
        include_system: bool = Query(True, description="是否包含系统角色"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取所有角色列表
    
    Args:
        include_system: 是否包含系统角色
        
    Returns:
        角色列表
    """
    try:
        from sqlalchemy import select

        query = select(Role)
        if not include_system:
            query = query.where(Role.is_system == False)

        result = await db.execute(query)
        roles = result.scalars().all()

        roles_list = []
        for role in roles:
            roles_list.append({
                'id': role.id,
                'name': role.name,
                'slug': role.slug,
                'description': role.description,
                'is_system': role.is_system,
                'parent_id': role.parent_id,
                'permission_count': len(role.permissions),
                'user_count': len(role.users),
                'created_at': role.created_at.isoformat() if role.created_at else None,
            })

        return ApiResponse(
            success=True,
            data={
                'roles': roles_list,
                'total': len(roles_list)
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.put("/roles/{role_id}/permissions", summary="更新角色权限")
async def update_role_permissions(
        role_id: int,
        permission_codes: List[str] = Body(..., description="权限代码列表"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新角色权限
    
    Args:
        role_id: 角色ID
        permission_codes: 权限代码列表
        
    Returns:
        更新结果
    """
    try:
        # 检查权限
        has_permission = await rbac_service.check_permission(db, current_user.id, 'user:update')
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        role = await db.get(
            rbac_service.__class__.__module__.replace('.rbac_service', '.rbac_service').split('.')[-1] + '.Role',
            role_id)

        role = await db.get(Role, role_id)

        if not role:
            return ApiResponse(success=False, error="Role not found")

        if role.is_system:
            return ApiResponse(success=False, error="Cannot modify system role permissions")

        # 清空现有权限
        role.permissions.clear()

        # 添加新权限
        from sqlalchemy import select

        for code in permission_codes:
            perm_stmt = select(Permission).where(Permission.code == code)
            perm_result = await db.execute(perm_stmt)
            perm = perm_result.scalar_one_or_none()
            if perm:
                role.permissions.append(perm)

        await db.commit()

        # 记录审计日志
        await rbac_service.log_permission_change(
            db=db,
            user_id=current_user.id,
            action='update_role_permissions',
            resource_type='role',
            resource_id=role_id,
            details={'permission_codes': permission_codes}
        )

        return ApiResponse(
            success=True,
            message="Role permissions updated successfully"
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/roles/{role_id}", summary="删除角色")
async def delete_role(
        role_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除角色（仅自定义角色）
    
    Args:
        role_id: 角色ID
        
    Returns:
        删除结果
    """
    try:
        # 检查权限
        has_permission = await rbac_service.check_permission(db, current_user.id, 'user:update')
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        role = await db.get(Role, role_id)

        if not role:
            return ApiResponse(success=False, error="Role not found")

        if role.is_system:
            return ApiResponse(success=False, error="Cannot delete system role")

        # 移除所有用户的该角色
        for user in role.users:
            user.roles.remove(role)

        await db.delete(role)
        await db.commit()

        # 记录审计日志
        await rbac_service.log_permission_change(
            db=db,
            user_id=current_user.id,
            action='delete_role',
            resource_type='role',
            resource_id=role_id
        )

        return ApiResponse(
            success=True,
            message="Role deleted successfully"
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 权限管理 ====================

@router.get("/permissions", summary="获取权限列表")
async def get_permissions(
        resource_type: Optional[str] = Query(None, description="资源类型过滤"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取所有权限列表
    
    Args:
        resource_type: 资源类型过滤
        
    Returns:
        权限列表
    """
    try:
        from sqlalchemy import select

        query = select(Permission).where(Permission.is_active == True)

        if resource_type:
            query = query.where(Permission.resource_type == resource_type)

        result = await db.execute(query)
        permissions = result.scalars().all()

        perms_list = []
        for perm in permissions:
            perms_list.append({
                'id': perm.id,
                'name': perm.name,
                'code': perm.code,
                'description': perm.description,
                'resource_type': perm.resource_type,
                'action': perm.action,
            })

        return ApiResponse(
            success=True,
            data={
                'permissions': perms_list,
                'total': len(perms_list)
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 用户角色分配 ====================

@router.post("/users/{user_id}/roles", summary="为用户分配角色")
async def assign_role_to_user(
        user_id: int,
        role_id: int = Body(..., description="角色ID"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    为用户分配角色
    
    Args:
        user_id: 用户ID
        role_id: 角色ID
        
    Returns:
        分配结果
    """
    try:
        # 检查权限
        has_permission = await rbac_service.check_permission(db, current_user.id, 'user:update')
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        await rbac_service.assign_role_to_user(db, user_id, role_id)

        # 记录审计日志
        await rbac_service.log_permission_change(
            db=db,
            user_id=current_user.id,
            action='assign_role',
            resource_type='user',
            resource_id=user_id,
            details={'role_id': role_id}
        )

        return ApiResponse(
            success=True,
            message="Role assigned successfully"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/users/{user_id}/roles/{role_id}", summary="从用户移除角色")
async def remove_role_from_user(
        user_id: int,
        role_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    从用户移除角色
    
    Args:
        user_id: 用户ID
        role_id: 角色ID
        
    Returns:
        移除结果
    """
    try:
        # 检查权限
        has_permission = await rbac_service.check_permission(db, current_user.id, 'user:update')
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        await rbac_service.remove_role_from_user(db, user_id, role_id)

        # 记录审计日志
        await rbac_service.log_permission_change(
            db=db,
            user_id=current_user.id,
            action='remove_role',
            resource_type='user',
            resource_id=user_id,
            details={'role_id': role_id}
        )

        return ApiResponse(
            success=True,
            message="Role removed successfully"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/users/{user_id}/permissions", summary="获取用户权限")
async def get_user_permissions(
        user_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户的所有权限
    
    Args:
        user_id: 用户ID
        
    Returns:
        权限列表
    """
    try:
        permissions = await rbac_service.get_user_permissions(db, user_id)

        return ApiResponse(
            success=True,
            data={
                'user_id': user_id,
                'permissions': permissions,
                'total': len(permissions)
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/check-permission", summary="检查权限")
async def check_permission(
        user_id: int = Body(..., description="用户ID"),
        permission_code: str = Body(..., description="权限代码"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    检查用户是否有指定权限
    
    Args:
        user_id: 用户ID
        permission_code: 权限代码
        
    Returns:
        权限检查结果
    """
    try:
        has_permission = await rbac_service.check_permission(db, user_id, permission_code)

        return ApiResponse(
            success=True,
            data={
                'user_id': user_id,
                'permission_code': permission_code,
                'has_permission': has_permission
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 审计日志 ====================

@router.get("/audit-logs", summary="获取权限审计日志")
async def get_audit_logs(
        user_id: Optional[int] = Query(None, description="用户ID过滤"),
        action: Optional[str] = Query(None, description="操作类型过滤"),
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(20, ge=1, le=100, description="每页数量"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取权限变更审计日志
    
    Args:
        user_id: 用户ID过滤
        action: 操作类型过滤
        page: 页码
        per_page: 每页数量
        
    Returns:
        审计日志列表和分页信息
    """
    try:
        from sqlalchemy import select, func
        query = select(PermissionAuditLog)

        if user_id:
            query = query.where(PermissionAuditLog.user_id == user_id)

        if action:
            query = query.where(PermissionAuditLog.action == action)

        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page).order_by(PermissionAuditLog.created_at.desc())

        result = await db.execute(query)
        logs = result.scalars().all()

        logs_list = []
        for log in logs:
            logs_list.append({
                'id': log.id,
                'user_id': log.user_id,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'details': log.details,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat() if log.created_at else None,
            })

        return ApiResponse(
            success=True,
            data={
                'logs': logs_list,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': (total + per_page - 1) // per_page
                }
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))
