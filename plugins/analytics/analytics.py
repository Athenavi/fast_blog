"""
高级数据分析API - 访客来源、热门文章、留存率等
"""

from fastapi import APIRouter, Depends, Query
from shared.services.advanced_analytics import advanced_analytics
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import admin_required_api
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["analytics"])


@router.get("/analytics/visitor-sources")
async def get_visitor_sources(
        days: int = Query(30, ge=1, le=365),
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """
    获取访客来源分析
    
    Args:
        days: 分析天数(1-365)
    """
    try:
        result = await advanced_analytics.get_visitor_sources(db, days)

        if result['success']:
            return ApiResponse(success=True, data=result['data'])
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"获取访客来源失败: {str(e)}")


@router.get("/analytics/popular-articles")
async def get_popular_articles(
        limit: int = Query(10, ge=1, le=100),
        days: int = Query(30, ge=1, le=365),
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """
    获取热门文章排行
    
    Args:
        limit: 返回数量
        days: 统计天数
    """
    try:
        result = await advanced_analytics.get_popular_articles(db, limit, days)

        if result['success']:
            return ApiResponse(success=True, data=result['data'])
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"获取热门文章失败: {str(e)}")


@router.get("/analytics/user-retention")
async def get_user_retention(
        days: int = Query(30, ge=7, le=90),
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """
    获取用户留存率
    
    Args:
        days: 分析周期
    """
    try:
        result = await advanced_analytics.get_user_retention_rate(db, days)

        if result['success']:
            return ApiResponse(success=True, data=result['data'])
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"获取留存率失败: {str(e)}")


@router.get("/analytics/conversion-funnel")
async def get_conversion_funnel(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """获取转化漏斗数据"""
    try:
        result = await advanced_analytics.get_conversion_funnel(db)

        if result['success']:
            return ApiResponse(success=True, data=result['data'])
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"获取转化漏斗失败: {str(e)}")


@router.get("/analytics/realtime")
async def get_realtime_stats(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """获取实时统计数据"""
    try:
        result = await advanced_analytics.get_realtime_stats(db)

        if result['success']:
            return ApiResponse(success=True, data=result['data'])
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"获取实时数据失败: {str(e)}")


@router.get("/analytics/dashboard-summary")
async def get_dashboard_summary(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """
    获取仪表盘综合摘要
    
    整合所有关键指标到一个接口
    """
    try:
        # 并行获取各项数据
        import asyncio

        # Windows + asyncpg 兼容性修复：顺序执行而不是并发执行
        retention = await advanced_analytics.get_user_retention_rate(db, 30)
        realtime = await advanced_analytics.get_realtime_stats(db)
        popular = await advanced_analytics.get_popular_articles(db, 5, 7)

        summary = {
            'realtime': realtime if isinstance(realtime, dict) else {'error': str(realtime)},
            'retention': retention if isinstance(retention, dict) else {'error': str(retention)},
            'popular_articles': popular if isinstance(popular, dict) else {'error': str(popular)},
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

        return ApiResponse(
            success=True,
            data=summary,
            message="仪表盘摘要获取成功"
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取仪表盘摘要失败: {str(e)}")
