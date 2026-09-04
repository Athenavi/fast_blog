"""
数据分析 API
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.articles.analytics import create_analytics_service
from src.api.v2._helpers import _catch
from src.auth import admin_required
from src.utils.database.unified_manager import get_db_session as get_async_db

# 平台级统计分析仅管理员可访问（含用户�?浏览�?趋势等内部数据）
router = APIRouter(tags=["analytics"], dependencies=[Depends(admin_required)])


@router.get("/overview")
@_catch
async def get_overview_stats(
        days: int = Query(30, ge=1, le=365, description="统计天数"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取概览统计数据

    Args:
        days: 统计天数
        db: 数据库会�?
    Returns:
        概览数据
    """
    service = create_analytics_service(db)
    stats = await service.get_overview_stats(days)

    return {
        'success': True,
        'data': stats,
    }


@router.get("/article-views-trend")
@_catch
async def get_article_views_trend(
        days: int = Query(30, ge=1, le=365, description="统计天数"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取文章浏览量趋�?
    Args:
        days: 统计天数
        db: 数据库会�?
    Returns:
        每日浏览量列...
    """
    service = create_analytics_service(db)
    trend = await service.get_article_views_trend(days)

    return {
        'success': True,
        'data': trend,
    }


@router.get("/popular-articles")
@_catch
async def get_popular_articles(
        limit: int = Query(10, ge=1, le=100, description="返回数量"),
        days: int = Query(7, ge=1, le=365, description="统计天数"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取热门文章

    Args:
        limit: 返回数量
        days: 统计天数
        db: 数据库会�?
    Returns:
        热门文章列表
    """
    service = create_analytics_service(db)
    articles = await service.get_popular_articles(limit, days)

    return {
        'success': True,
        'data': articles,
    }


@router.get("/category-distribution")
@_catch
async def get_category_distribution(
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取分类分布

    Args:
        db: 数据库会�?
    Returns:
        分类统计列表
    """
    service = create_analytics_service(db)
    distribution = await service.get_category_distribution()

    return {
        'success': True,
        'data': distribution,
    }


@router.get("/user-activity")
@_catch
async def get_user_activity(
        days: int = Query(30, ge=1, le=365, description="统计天数"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户活动统计

    Args:
        days: 统计天数
        db: 数据库会�?
    Returns:
        用户活动数据
    """
    service = create_analytics_service(db)
    activity = await service.get_user_activity(days)

    return {
        'success': True,
        'data': activity,
    }


@router.get("/content-performance")
@_catch
async def get_content_performance(
        days: int = Query(30, ge=1, le=365, description="统计天数"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取内容表现分析

    Args:
        days: 统计天数
        db: 数据库会�?
    Returns:
        内容表现数据
    """
    service = create_analytics_service(db)
    performance = await service.get_content_performance(days)

    return {
        'success': True,
        'data': performance,
    }


@router.get("/traffic-sources")
@_catch
async def get_traffic_sources(
        days: int = Query(30, ge=1, le=365, description="统计天数"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取流量来源分析

    Args:
        days: 统计天数
        db: 数据库会�?
    Returns:
        流量来源列表
    """
    service = create_analytics_service(db)
    sources = await service.get_traffic_sources(days)

    return {
        'success': True,
        'data': sources,
    }


@router.get("/device-stats")
@_catch
async def get_device_stats(
        days: int = Query(30, ge=1, le=365, description="统计天数"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取设备统计

    Args:
        days: 统计天数
        db: 数据库会�?
    Returns:
        设备分布数据
    """
    service = create_analytics_service(db)
    stats = await service.get_device_stats(days)

    return {
        'success': True,
        'data': stats,
    }
