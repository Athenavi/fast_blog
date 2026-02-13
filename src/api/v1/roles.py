"""
角色和权限管理API v1
迁移自 src/blueprints/role.py
"""

from datetime import datetime

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.auth_deps import admin_required_api
from src.extensions import get_async_db_session as get_async_db
from src.models import User, Role, Permission, UserRole, RolePermission

# 创建API路由器
router = APIRouter(tags=["role"])


@router.get('/admin/role/search')
async def admin_roles_search(
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        search: str = Query(""),
        current_user=Depends(admin_required_api)
):
    """获取角色列表，并支持分页和搜索"""
    try:
        # 过滤角色数据，根据搜索关键词
        from sqlalchemy import select
        query = select(Role)
        if search:
            query = query.filter(
                or_(Role.name.ilike(f'%{search}%'), Role.description.ilike(f'%{search}%'))
            )

        # 获取所有匹配的角色
        roles = query.all()

        # 手动分页
        total = len(roles)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_roles = roles[start:end]

        # 返回结果
        roles_data = [{
            'id': role.id,
            'name': role.name,
            'description': role.description,
            'permissions': [
                {
                    'id': perm.id,
                    'code': perm.code,
                    'description': perm.description
                } for perm in role.permissions
            ],
            'created_at': role.__dict__.get('created_at').isoformat() if hasattr(role,
                                                                                 'created_at') and role.created_at else datetime.now().isoformat()
        } for role in paginated_roles]

        return JSONResponse({
            'success': True,
            'data': {
                'data': roles_data,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': (total + per_page - 1) // per_page  # 计算总页数
                }
            }
        })
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': str(e)
        })


@router.post('/admin/role')
async def create_role(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """创建新角色"""

    try:
        data = await request.json()

        required_fields = ['name', 'description']
        for field in required_fields:
            if not data.get(field):
                return JSONResponse({
                    'success': False,
                    'message': f'缺少必填字段: {field}'
                }, status_code=400)

        new_role = Role(
            name=data['name'],
            description=data['description']
        )

        db.add(new_role)
        db.commit()
        db.refresh(new_role)

        # 添加权限关联
        if 'permission_ids' in data:
            for permission_id in data['permission_ids']:
                from sqlalchemy import select
                permission_query = select(Permission).where(Permission.id == permission_id)
                permission_result = await db.execute(permission_query)
                permission = permission_result.scalar_one_or_none()
                if permission:
                    new_role.permissions.append(permission)

        db.commit()

        return JSONResponse({
            'success': True,
            'message': '角色创建成功',
            'data': {
                'id': new_role.id,
                'name': new_role.name,
                'description': new_role.description,
                'permissions': [
                    {
                        'id': perm.id,
                        'code': perm.code,
                        'description': perm.description
                    } for perm in new_role.permissions
                ],
                'created_at': new_role.__dict__.get('created_at').isoformat() if hasattr(new_role,
                                                                                         'created_at') and new_role.created_at else datetime.now().isoformat()
            }
        }, status_code=201)

    except Exception as e:
        db.rollback()
        return JSONResponse({
            'success': False,
            'message': f'创建角色失败: {str(e)}'
        }, status_code=500)


@router.get('/admin/role/{role_id}')
async def admin_role_detail(
        role_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """获取角色详情"""

    try:
        from sqlalchemy import select
        role_query = select(Role).where(Role.id == role_id)
        role_result = await db.execute(role_query)
        role = role_result.scalar_one_or_none()

        if role is None:
            return JSONResponse({
                'success': False,
                'message': f'角色ID {role_id} 不存在'
            }, status_code=404)

        role_data = {
            'id': role.id,
            'name': role.name,
            'description': role.description,
            'permissions': [
                {
                    'id': permission.id,
                    'code': permission.code,
                    'description': permission.description
                } for permission in role.permissions
            ]
        }

        return JSONResponse({
            'success': True,
            'data': role_data
        }, status_code=200)

    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'获取角色详情失败: {str(e)}'
        }, status_code=500)


@router.put('/admin/role/{role_id}')
async def update_role(
        role_id: int,
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """更新角色"""

    try:
        role = db.query(Role).get(role_id)  # 直接使用 role_id 而不是 id=role_id
        data = await request.json()
        print(data)

        if 'name' in data:
            role.name = data['name']
        if 'description' in data:
            role.description = data['description']

        # 更新权限关联
        if 'permission_ids' in data:
            role.permissions.clear()
            for permission_id in data['permission_ids']:
                permission = db.query(Permission).get(permission_id)  # 直接使用 permission_id 而不是 id=permission_id
                if permission:
                    role.permissions.append(permission)

        db.commit()

        return JSONResponse({
            'success': True,
            'message': '角色更新成功',
            'data': {
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'permissions': [
                    {
                        'id': perm.id,
                        'code': perm.code,
                        'description': perm.description
                    } for perm in role.permissions
                ],
                'created_at': role.__dict__.get('created_at').isoformat() if hasattr(role,
                                                                                     'created_at') and role.created_at else datetime.now().isoformat()
            }
        }, status_code=200)

    except Exception as e:
        db.rollback()
        return JSONResponse({
            'success': False,
            'message': f'更新角色失败: {str(e)}'
        }, status_code=500)


@router.delete('/admin/role/{role_id}')
async def delete_role(
        role_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """删除角色"""

    try:
        role = db.query(Role).filter_by(id=role_id).first()

        if len(role.users) > 0:
            return JSONResponse({
                'success': False,
                'message': f'无法删除角色，该角色已分配给 {len(role.users)} 个用户'
            }, status_code=409)

        role_name = role.name
        db.delete(role)
        db.commit()

        return JSONResponse({
            'success': True,
            'message': f'角色 "{role_name}" 删除成功'
        }, status_code=200)

    except Exception as e:
        db.rollback()
        return JSONResponse({
            'success': False,
            'message': f'删除角色失败: {str(e)}'
        }, status_code=500)


@router.get('/admin/permission')
async def get_permissions(
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        search: str = Query(""),
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """获取权限列表"""

    try:
        from sqlalchemy import select
        query = select(Permission)

        if search:
            query = query.filter(
                or_(
                    Permission.code.contains(search),
                    Permission.description.contains(search)
                )
            )

        # 手动计算分页
        total = query.count()
        pages = (total + per_page - 1) // per_page  # 计算总页数
        offset = (page - 1) * per_page

        # 获取当前页的数据
        permissions = query.offset(offset).limit(per_page).all()

        permissions_data = []
        for permission in permissions:
            permissions_data.append({
                'id': permission.id,
                'code': permission.code,
                'description': permission.description,
                'role_count': len(permission.roles)
            })

        return JSONResponse({
            'success': True,
            'data': {
                'data': permissions_data,
                'pagination': {
                    'page': page,
                    'pages': pages,
                    'per_page': per_page,
                    'total': total,
                    'has_next': page < pages,
                    'has_prev': page > 1
                }
            }
        }, status_code=200)

    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'获取权限列表失败: {str(e)}'
        }, status_code=500)


@router.post('/admin/permission')
async def create_permission(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """创建新权限"""

    try:
        data = await request.json()

        required_fields = ['code', 'description']
        for field in required_fields:
            if not data.get(field):
                return JSONResponse({
                    'success': False,
                    'message': f'缺少必填字段: {field}'
                }, status_code=400)

        new_permission = Permission(
            code=data['code'],
            description=data['description']
        )

        db.add(new_permission)
        db.commit()
        db.refresh(new_permission)

        return JSONResponse({
            'success': True,
            'message': '权限创建成功',
            'data': {
                'id': new_permission.id,
                'code': new_permission.code,
                'description': new_permission.description
            }
        }, status_code=201)

    except Exception as e:
        db.rollback()
        return JSONResponse({
            'success': False,
            'message': f'创建权限失败: {str(e)}'
        }, status_code=500)


@router.put('/admin/permission/{permission_id}')
async def update_permission(
        permission_id: int,
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """更新权限"""

    try:
        from sqlalchemy import select
        permission_query = select(Permission).where(Permission.id == permission_id)
        permission_result = await db.execute(permission_query)
        permission = permission_result.scalar_one_or_none()
        if not permission:
            return JSONResponse({
                'success': False,
                'message': f'权限ID {permission_id} 不存在'
            }, status_code=404)

        data = await request.json()

        if 'code' in data:
            permission.code = data['code']
        if 'description' in data:
            permission.description = data['description']

        db.commit()

        return JSONResponse({
            'success': True,
            'message': '权限更新成功',
            'data': {
                'id': permission.id,
                'code': permission.code,
                'description': permission.description
            }
        }, status_code=200)

    except Exception as e:
        db.rollback()
        return JSONResponse({
            'success': False,
            'message': f'更新权限失败: {str(e)}'
        }, status_code=500)


@router.delete('/admin/permission/{permission_id}')
async def delete_permission(
        permission_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """删除权限"""

    try:
        permission = db.query(Permission).filter_by(id=permission_id).first()
        if permission is None:
            return JSONResponse({
                'success': False,
                'message': f'权限ID {permission_id} 不存在'
            }, status_code=404)

        if len(permission.roles) > 0:
            return JSONResponse({
                'success': False,
                'message': f'无法删除权限，该权限已分配给 {len(permission.roles)} 个角色'
            }, status_code=409)

        permission_code = permission.code
        db.delete(permission)
        db.commit()

        return JSONResponse({
            'success': True,
            'message': f'权限 "{permission_code}" 删除成功'
        }, status_code=200)

    except Exception as e:
        db.rollback()
        return JSONResponse({
            'success': False,
            'message': f'删除权限失败: {str(e)}'
        }, status_code=500)


@router.get('/admin/user/{user_id}/roles')
async def get_user_roles(
        user_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """获取用户的角色"""
    try:
        from sqlalchemy import select
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if user is None:
            return JSONResponse({
                'success': False,
                'message': '用户不存在'
            }, status_code=404)

        user_roles = []
        for role in user.roles:
            user_roles.append({
                'id': role.id,
                'name': role.name,
                'description': role.description
            })

        return JSONResponse({
            'success': True,
            'data': {
                'user_id': user.id,
                'username': user.username,
                'roles': user_roles
            }
        }, status_code=200)

    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'获取用户角色失败: {str(e)}'
        }, status_code=500)


@router.put('/admin/user/{user_id}/roles')
async def update_user_roles(
        user_id: int,
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """更新用户角色"""
    try:
        from sqlalchemy import select
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        if user is None:
            return JSONResponse({
                'success': False,
                'message': '用户不存在'
            }, status_code=404)

        data = await request.json()

        if 'role_ids' not in data:
            return JSONResponse({
                'success': False,
                'message': '缺少角色ID列表'
            }, status_code=400)

        # 清除现有角色
        user.roles.clear()

        for role_id in data['role_ids']:
            from sqlalchemy import select
            role_query = select(Role).where(Role.id == role_id)
            role_result = await db.execute(role_query)
            role = role_result.scalar_one_or_none()
            if role:
                user.roles.append(role)

        db.commit()

        return JSONResponse({
            'success': True,
            'message': '用户角色更新成功',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'role_count': len(user.roles)
            }
        }, status_code=200)

    except Exception as e:
        db.rollback()
        return JSONResponse({
            'success': False,
            'message': f'更新用户角色失败: {str(e)}'
        }, status_code=500)


@router.get('/admin/role-permission/stats')
async def get_role_permission_stats(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """获取角色权限统计信息"""
    try:
        from sqlalchemy import select
        total_roles_query = select(func.count(Role.id))
        total_roles_result = await db.execute(total_roles_query)
        total_roles = total_roles_result.scalar()
        from sqlalchemy import select
        total_permissions_query = select(func.count(Permission.id))
        total_permissions_result = await db.execute(total_permissions_query)
        total_permissions = total_permissions_result.scalar()
        from sqlalchemy import select
        total_user_roles_query = select(func.count(UserRole.id))
        total_user_roles_result = await db.execute(total_user_roles_query)
        total_user_roles = total_user_roles_result.scalar()
        from sqlalchemy import select
        total_role_permissions_query = select(func.count(RolePermission.id))
        total_role_permissions_result = await db.execute(total_role_permissions_query)
        total_role_permissions = total_role_permissions_result.scalar()

        return JSONResponse({
            'success': True,
            'data': {
                'total_roles': total_roles,
                'total_permissions': total_permissions,
                'total_user_roles': total_user_roles,
                'total_role_permissions': total_role_permissions
            }
        }, status_code=200)

    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'获取统计信息失败: {str(e)}'
        }, status_code=500)


@router.get('/admin/role-management/roles')
async def get_role_management_roles(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """获取角色管理页面所需的角色列表"""
    try:
        from sqlalchemy import select
        roles_query = select(Role)
        roles_result = await db.execute(roles_query)
        roles = roles_result.scalars().all()
        roles_data = []
        for role in roles:
            roles_data.append({
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "created_at": role.__dict__.get('created_at').isoformat() if hasattr(role,
                                                                                     'created_at') and role.created_at else datetime.now().isoformat(),
                "permissions": [{
                    "id": perm.id,
                    "name": perm.code,
                    "description": perm.description
                } for perm in role.permissions]
            })

        return JSONResponse({
            'success': True,
            'data': roles_data
        })
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'获取角色列表失败: {str(e)}'
        }, status_code=500)
