"""search_analytics 模块路由

::

    GET /api/v3/analytics/search/summary       搜索概况
    GET /api/v3/analytics/search/popular       热门关键词
    GET /api/v3/analytics/search/zero-result   无结果关键词
    GET /api/v3/analytics/search/trend         搜索趋势

权限码：``settings:view``
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.modules.analytics.search.service import search_analytics_service

router = APIRouter(prefix="/search", tags=["analytics-search"])


@router.get("/summary", response_model=ResponseModel, summary="搜索概况")
async def search_summary(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
    days: Optional[int] = Query(default=None, ge=1, le=365),
) -> dict:
    return resp.success(await search_analytics_service.summary(db, days=days))


@router.get("/popular", response_model=ResponseModel, summary="热门关键词")
async def popular_keywords(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
    limit: int = Query(default=20, ge=1, le=200),
    days: Optional[int] = Query(default=None, ge=1, le=365),
) -> dict:
    return resp.success(await search_analytics_service.popular(db, limit=limit, days=days))


@router.get("/zero-result", response_model=ResponseModel, summary="无结果关键词")
async def zero_result_keywords(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
    limit: int = Query(default=20, ge=1, le=200),
    days: Optional[int] = Query(default=None, ge=1, le=365),
) -> dict:
    return resp.success(await search_analytics_service.zero_result(db, limit=limit, days=days))


@router.get("/trend", response_model=ResponseModel, summary="搜索趋势")
async def search_trend(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    return resp.success(await search_analytics_service.trend(db, days=days))
