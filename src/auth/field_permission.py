"""
字段级权限控制装饰器
基于 FieldPermission 模型检查用户对模型字段的读写权限
"""

from functools import wraps
from typing import List, Optional

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.security import FieldPermission
from shared.models.rbac import UserRole
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db


async def get_field_permissions(
    db: AsyncSession,
    role_ids: List[int],
    model_name: str,
    field_name: str
) -> tuple[bool, bool]:
    """
    获取指定角色对某模型字段的读写权限

    Returns:
        (can_read, can_write)
    """
    if not role_ids:
        return True, False

    result = await db.execute(
        select(FieldPermission)
        .where(
            FieldPermission.role_id.in_(role_ids),
            FieldPermission.model_name == model_name,
            FieldPermission.field_name == field_name,
        )
    )
    permissions = result.scalars().all()

    if not permissions:
        # 无明确配置时: 可读、不可写
        return True, False

    can_read = any(p.can_read for p in permissions)
    can_write = any(p.can_write for p in permissions)
    return can_read, can_write


def check_field_permission(model_name: str, field_name: str, action: str = "read"):
    """
    字段级权限检查装饰器

    Args:
        model_name: 模型名称 (如 "User", "Article")
        field_name: 字段名称 (如 "email", "phone")
        action: "read" 或 "write"

    Usage:
        @router.get("/users/{id}")
        @check_field_permission("User", "email", "read")
        async def get_user(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户
            request = kwargs.get("request")
            current_user = kwargs.get("current_user")

            if not current_user and request:
                current_user = getattr(request.state, "user", None)

            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")

            # 获取用户角色
            db = kwargs.get("db")
            if db is None:
                async with get_async_db() as session:
                    result = await session.execute(
                        select(UserRole).where(UserRole.user_id == current_user.id)
                    )
                    user_roles = result.scalars().all()
                    role_ids = [ur.role_id for ur in user_roles]

                    can_read, can_write = await get_field_permissions(
                        session, role_ids, model_name, field_name
                    )

                    if action == "read" and not can_read:
                        raise HTTPException(status_code=403, detail=f"No read permission on {model_name}.{field_name}")
                    if action == "write" and not can_write:
                        raise HTTPException(status_code=403, detail=f"No write permission on {model_name}.{field_name}")
            else:
                result = await db.execute(
                    select(UserRole).where(UserRole.user_id == current_user.id)
                )
                user_roles = result.scalars().all()
                role_ids = [ur.role_id for ur in user_roles]

                can_read, can_write = await get_field_permissions(
                    db, role_ids, model_name, field_name
                )

                if action == "read" and not can_read:
                    raise HTTPException(status_code=403, detail=f"No read permission on {model_name}.{field_name}")
                if action == "write" and not can_write:
                    raise HTTPException(status_code=403, detail=f"No write permission on {model_name}.{field_name}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def filter_fields_by_permission(
    user_id: int,
    model_name: str,
    fields: dict,
    action: str = "read"
) -> dict:
    """
    根据用户权限过滤字段

    这是一个同步辅助函数，适用于在序列化/响应构建阶段调用。
    注意: 为了简洁，此函数使用新的数据库连接。

    Returns:
        过滤后的字段字典
    """
    import asyncio
    from src.utils.database.unified_manager import db_manager

    async def _filter():
        async with db_manager.get_session() as db:
            result = await db.execute(
                select(UserRole).where(UserRole.user_id == user_id)
            )
            user_roles = result.scalars().all()
            role_ids = [ur.role_id for ur in user_roles]

            filtered = {}
            for field_name, value in fields.items():
                can_read, _ = await get_field_permissions(db, role_ids, model_name, field_name)
                if can_read:
                    filtered[field_name] = value
            return filtered

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_filter())
    finally:
        loop.close()
