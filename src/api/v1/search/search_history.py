"""
搜索历史 API
提供用户搜索历史的查询功能
"""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.search_history import SearchHistory
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search-history"])


@router.get('/history')
async def get_search_history(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户的搜索历史
    """
    try:
        # 获取当前用户的搜索历史，按时间倒序排列，最多返回 10 条
        query = select(SearchHistory).where(
            SearchHistory.user_id == current_user.id
        ).order_by(desc(SearchHistory.created_at)).limit(10)

        result = await db.execute(query)
        history_list = result.scalars().all()

        # 转换为字典列表
        history_data = [history.to_dict() for history in history_list]

        return {
            'success': True,
            'data': history_data
        }
    except Exception as e:
        logger.error(f"获取搜索历史失败：{str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
