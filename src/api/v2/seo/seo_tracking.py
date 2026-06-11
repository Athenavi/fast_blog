"""
SEO 效果追踪 API
提供搜索引擎流量、关键词排名、流量来源等查询功能
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query

from shared.services.seo.seo_tracker import seo_tracker
from src.api.v2._helpers import ok, fail, _catch
from src.auth.auth_deps import get_current_active_user, admin_required as admin_required_api

router = APIRouter(tags=["seo-tracking"])


@router.get("/search-traffic", summary="获取搜索引擎流量汇总")
@_catch
async def get_search_traffic(
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(admin_required_api)
):
    """获取搜索引擎流量汇总数据"""
    summary = seo_tracker.get_search_traffic_summary(days)
    return ok(data=summary)


@router.get("/top-keywords", summary="获取热门关键词")
@_catch
async def get_top_keywords(
        limit: int = Query(20, ge=1, le=100, description="返回数量"),
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(admin_required_api)
):
    """获取热门搜索关键词"""
    keywords = seo_tracker.get_top_keywords(limit, days)
    return ok(data={'keywords': keywords, 'count': len(keywords), 'period_days': days})


@router.get("/article/{article_id}/performance", summary="获取文章 SEO 表现")
@_catch
async def get_article_seo_performance(
        article_id: int,
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(get_current_active_user)
):
    """获取指定文章的 SEO 表现数据"""
    performance = seo_tracker.get_article_seo_performance(article_id, days)
    return ok(data=performance)


@router.get("/traffic-sources", summary="获取流量来源分析")
@_catch
async def get_traffic_sources(
        article_id: int = Query(None, description="文章ID（可选）"),
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(admin_required_api)
):
    """获取流量来源分析"""
    sources = seo_tracker.get_traffic_sources(article_id, days)
    return ok(data=sources)


@router.post("/track-visit", summary="记录页面访问")
@_catch
async def track_visit(
        article_id: int = Query(..., description="文章ID"),
        referrer: str = Query('', description="来源URL"),
        user_agent: str = Query('', description="用户代理"),
):
    """记录页面访问用于 SEO 分析"""
    seo_tracker.track_visit(
        article_id=article_id,
        referrer=referrer,
        user_agent=user_agent,
    )
    return ok(data=None, message='访问已记录')


@router.get("/dashboard", summary="获取 SEO 仪表板数据")
@_catch
async def get_seo_dashboard(
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(admin_required_api)
):
    """获取 SEO 仪表板综合数据"""
    traffic_summary = seo_tracker.get_search_traffic_summary(days)
    top_keywords = seo_tracker.get_top_keywords(10, days)
    traffic_sources = seo_tracker.get_traffic_sources(days=days)
    return ok(data={
        'traffic_summary': traffic_summary,
        'top_keywords': top_keywords,
        'traffic_sources': traffic_sources,
        'period_days': days,
    })
