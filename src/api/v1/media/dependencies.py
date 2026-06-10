"""
媒体包依赖项
"""


from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.media import Media
from shared.models.user import User
from src.setting import BaseConfig
from src.unified_logger import default_logger as logger


async def get_user_storage_used(user_id: int, db: AsyncSession):
    """获取用户已使用的存储空间（直接使用 Media.file_size，避免 FileHash JOIN）"""
    try:
        storage_used_query = select(func.sum(Media.file_size)).where(Media.user == user_id)
        storage_used_result = await db.execute(storage_used_query)
        storage_used = storage_used_result.scalar() or 0
        return int(storage_used)
    except Exception as e:
        logger.error(f"获取用户存储使用量失败: {str(e)}")
        return 0


async def get_user_storage_limit(user_id: int, db: AsyncSession):
    """根据用户VIP等级获取存储限制"""
    try:
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        if not user:
            return BaseConfig.USER_FREE_STORAGE_LIMIT

        base_limit = BaseConfig.USER_FREE_STORAGE_LIMIT
        if user.vip_level == 1:
            return base_limit * 2
        elif user.vip_level == 2:
            return base_limit * 10
        elif user.vip_level >= 3:
            return base_limit * 40
        return base_limit
    except Exception as e:
        logger.error(f"获取用户存储限制失败: {str(e)}")
        return BaseConfig.USER_FREE_STORAGE_LIMIT
