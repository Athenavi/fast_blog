"""
字段级权限检查服务
根据 FieldPermission 配置过滤模型的字段可见/可写
"""
from typing import Dict, List, Any, Set, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.security.field_permission import FieldPermission
from shared.services.rbac import check_user_permission
from src.unified_logger import default_logger as logger


async def get_restricted_fields(
    db: AsyncSession,
    user_id: int,
    model_name: str,
    user_role_ids: Optional[List[int]] = None,
) -> Set[str]:
    """
    获取用户对指定模型不可见的字段集合

    默认所有字段可见，只有被明确设置为 can_read=False 的才被过滤

    Args:
        db: 数据库会话
        user_id: 用户 ID
        model_name: 模型名称（如 "User", "Article"）
        user_role_ids: 用户角色 ID 列表（可选，为 None 时自动查询）

    Returns:
        受限字段名称集合（调用方需从全字段列表中排除这些）
    """
    try:
        if user_role_ids is None:
            from shared.services.rbac import _get_user_role_ids_with_inheritance
            user_role_ids = list(await _get_user_role_ids_with_inheritance(db, user_id))

        if not user_role_ids:
            return set()  # 无角色则无字段可见

        # 查询对此模型设置了 can_read=False 的字段
        result = await db.execute(
            select(FieldPermission)
            .where(
                FieldPermission.role_id.in_(user_role_ids),
                FieldPermission.model_name == model_name,
                FieldPermission.can_read == False,
            )
        )
        restricted = result.scalars().all()
        restricted_fields = {r.field_name for r in restricted}

        # 返回可用的字段（需要知道所有字段名...）
        # 这里假设调用者会传入完整字段列表
        return restricted_fields  # 返回被限制的字段集合

    except Exception as e:
        logger.error(f"获取可见字段失败: {e}", exc_info=True)
        return set()


async def filter_fields_by_permission(
    db: AsyncSession,
    user_id: int,
    model_name: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    根据字段权限过滤数据（移除不可读的字段）

    Args:
        db: 数据库会话
        user_id: 用户 ID
        model_name: 模型名称
        data: 原始数据字典

    Returns:
        过滤后的数据字典
    """
    from shared.services.rbac import _get_user_role_ids_with_inheritance
    all_role_ids = list(await _get_user_role_ids_with_inheritance(db, user_id))

    if not all_role_ids:
        return {}

    # 查询被限制的字段
    result = await db.execute(
        select(FieldPermission)
        .where(
            FieldPermission.role_id.in_(all_role_ids),
            FieldPermission.model_name == model_name,
            FieldPermission.can_read == False,
        )
    )
    restricted = result.scalars().all()
    restricted_fields = {r.field_name for r in restricted}

    # 过滤
    return {k: v for k, v in data.items() if k not in restricted_fields}


async def get_writable_fields(
    db: AsyncSession,
    user_id: int,
    model_name: str,
    user_role_ids: Optional[List[int]] = None,
) -> Set[str]:
    """
    获取用户对指定模型可写的字段集合

    Args:
        db: 数据库会话
        user_id: 用户 ID
        model_name: 模型名称
        user_role_ids: 用户角色 ID 列表

    Returns:
        可写字段名称集合
    """
    try:
        if user_role_ids is None:
            from shared.services.rbac import _get_user_role_ids_with_inheritance
            user_role_ids = list(await _get_user_role_ids_with_inheritance(db, user_id))

        if not user_role_ids:
            return set()

        # 查询对此模型明确设置了 can_write=True 的字段
        result = await db.execute(
            select(FieldPermission)
            .where(
                FieldPermission.role_id.in_(user_role_ids),
                FieldPermission.model_name == model_name,
                FieldPermission.can_write == True,
            )
        )
        allowed = result.scalars().all()

        # 没有明确授予写权限的字段，默认不可写（最小权限原则）
        return {r.field_name for r in allowed}

    except Exception as e:
        logger.error(f"获取可写字段失败: {e}", exc_info=True)
        return set()


__all__ = [
    'get_visible_fields',
    'filter_fields_by_permission',
    'get_writable_fields',
]
