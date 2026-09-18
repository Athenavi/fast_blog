"""dashboard 模块路由

::

    GET /api/v3/analytics/dashboard/overview         统计概览
    GET /api/v3/analytics/dashboard/trend            最近 N 天趋势
    GET /api/v3/analytics/dashboard/recent-articles  最近文章
    GET /api/v3/analytics/dashboard/recent-comments  最近评论
    GET /api/v3/analytics/dashboard/top-articles     浏览量排行

权限码：``settings:view``（概览）/ ``article:view``（文章类）/ ``comment:view``（评论类）
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.modules.analytics.dashboard.service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["analytics-dashboard"])


@router.get("/overview", response_model=ResponseModel, summary="统计概览")
async def overview(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
) -> dict:
    return resp.success(await dashboard_service.overview(db))


@router.get("/trend", response_model=ResponseModel, summary="最近 N 天趋势")
async def trend(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    return resp.success(await dashboard_service.trend(db, days=days))


@router.get("/recent-articles", response_model=ResponseModel, summary="最近文章")
async def recent_articles(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    limit: int = Query(default=5, ge=1, le=50),
) -> dict:
    return resp.success(await dashboard_service.recent_articles(db, limit=limit))


@router.get("/recent-comments", response_model=ResponseModel, summary="最近评论")
async def recent_comments(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    limit: int = Query(default=5, ge=1, le=50),
) -> dict:
    return resp.success(await dashboard_service.recent_comments(db, limit=limit))


@router.get("/top-articles", response_model=ResponseModel, summary="浏览量排行")
async def top_articles(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    limit: int = Query(default=10, ge=1, le=100),
    days: Optional[int] = Query(default=None, ge=1, le=365),
) -> dict:
    return resp.success(await dashboard_service.top_articles(db, limit=limit, days=days))
