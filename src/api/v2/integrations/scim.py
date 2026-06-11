"""
SCIM 用户同步 API
模拟 SCIM (System for Cross-domain Identity Management) 标准，
提供外部用户同步、已同步用户列表和分组聚合功能
"""
from functools import wraps
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db

router = APIRouter(tags=["scim"])

# 用于跟踪已同步的外部用户 ID 映射（内存存储，生产环境应持久化）
# external_id -> user_id
_synced_users = {}


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            return fail(str(e))
    return wrapper


async def _require_superuser(current_user):
    """检查超级管理员权限"""
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


@router.post("/integrations/scim/users", summary="推送外部用户同步请求")
@_catch
async def push_scim_user(
        external_id: str = Body(..., description="外部用户 ID"),
        username: str = Body(..., description="用户名"),
        email: str = Body(..., description="邮箱"),
        groups: Optional[List[str]] = Body(None, description="用户分组列表"),
        active: bool = Body(True, description="是否激活"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    推送外部用户同步请求（模拟 SCIM 标准）
    查找或创建 User，更新属性，返回用户信息
    （需要超级管理员权限）
    """
    await _require_superuser(current_user)

    from sqlalchemy import select
    from shared.models.user.user import User
    import datetime

    # 尝试通过 external_id 映射查找已同步的用户
    user_id = _synced_users.get(external_id)
    user = None

    if user_id:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

    # 如果未找到，尝试通过 email 查找
    if not user:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

    # 如果仍未找到，创建新用户
    if not user:
        user = User(
            username=username,
            email=email,
            is_active=active,
            date_joined=datetime.datetime.now(),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # 记录同步映射
        _synced_users[external_id] = user.id
    else:
        # 更新已有用户属性
        user.username = username
        user.email = email
        user.is_active = active
        await db.commit()
        await db.refresh(user)

        # 记录同步映射
        _synced_users[external_id] = user.id

    return ok(data={
        'id': user.id,
        'external_id': external_id,
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
        'groups': groups or [],
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
    }, msg="User synced successfully")


@router.get("/integrations/scim/users", summary="列出已同步的外部用户")
@_catch
async def list_scim_users(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """列出已同步的外部用户（从 User 模型读取标记了 external_id 的用户）（需要超级管理员权限）"""
    await _require_superuser(current_user)

    from sqlalchemy import select
    from shared.models.user.user import User

    users_list = []
    for ext_id, uid in _synced_users.items():
        stmt = select(User).where(User.id == uid)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            users_list.append({
                'id': user.id,
                'external_id': ext_id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
            })

    return ok(data={
        'users': users_list,
        'total': len(users_list),
    })


@router.get("/integrations/scim/groups", summary="列出同步的用户分组")
@_catch
async def list_scim_groups(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """列出同步的用户分组（从 User 模型聚合 role/group 字段）（需要超级管理员权限）"""
    await _require_superuser(current_user)

    from sqlalchemy import select, func
    from shared.models.user.user import User

    # 聚合 is_superuser 和 is_staff 作为分组信息
    stmt = select(
        User.is_superuser,
        User.is_staff,
        func.count().label('count')
    ).group_by(User.is_superuser, User.is_staff)

    result = await db.execute(stmt)
    rows = result.all()

    groups = []
    for row in rows:
        group_name = 'admin' if row.is_superuser else ('staff' if row.is_staff else 'user')
        groups.append({
            'name': group_name,
            'display_name': 'Administrators' if row.is_superuser else ('Staff' if row.is_staff else 'Regular Users'),
            'count': row.count,
            'members': [],
        })

    return ok(data={
        'groups': groups,
        'total': len(groups),
    })
