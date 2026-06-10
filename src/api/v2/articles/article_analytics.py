"""
文章分析 API - V2 优化版
提供文章阅读量趋势、来源渠道、读者分布等分析功能
"""
from functools import wraps

from fastapi import APIRouter, Depends, Query

from shared.models.user import User as UserModel
from shared.services.articles.article_analytics_service import article_analytics_service
from src.api.v2._base import ApiResponse
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import get_current_active_user


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return fail(f"操作失败: {e}")
    return wrapper


router = APIRouter(tags=["article-analytics"])


@router.get("/{article_id}/stats")
@_catch
async def get_article_stats(article_id: int, days: int = Query(30, ge=1, le=365),
                             current_user: UserModel = Depends(get_current_active_user)):
    return ok(article_analytics_service.get_article_stats(article_id, days))


@router.get("/{article_id}/trend")
@_catch
async def get_article_trend(article_id: int, days: int = Query(30, ge=1, le=365),
                             current_user: UserModel = Depends(get_current_active_user)):
    return ok(article_analytics_service.get_article_trend(article_id, days))


@router.get("/{article_id}/sources")
@_catch
async def get_article_sources(article_id: int, days: int = Query(30, ge=1, le=365),
                               current_user: UserModel = Depends(get_current_active_user)):
    return ok(article_analytics_service.get_article_sources(article_id, days))


@router.get("/{article_id}/regions")
@_catch
async def get_article_regions(article_id: int, days: int = Query(30, ge=1, le=365),
                               current_user: UserModel = Depends(get_current_active_user)):
    return ok(article_analytics_service.get_article_regions(article_id, days))


@router.get("/{article_id}/full-report")
@_catch
async def get_full_report(article_id: int, days: int = Query(30, ge=1, le=365),
                           current_user: UserModel = Depends(get_current_active_user)):
    return ok(article_analytics_service.get_full_report(article_id, days))


@router.get("/top-articles")
@_catch
async def get_top_articles(limit: int = Query(10, ge=1, le=100), days: int = Query(30, ge=1, le=365),
                            current_user: UserModel = Depends(get_current_active_user)):
    return ok(article_analytics_service.get_top_articles(limit, days))
