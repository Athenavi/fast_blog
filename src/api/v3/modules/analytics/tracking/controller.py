"""analytics/tracking 模块路由（埋点上报 + 阅读聚合）

**上报（可选登录，访客亦可）**::

    POST /api/v3/analytics/tracking/page-view       页面浏览
    POST /api/v3/analytics/tracking/event           行为事件
    POST /api/v3/analytics/tracking/search          搜索记录
    POST /api/v3/analytics/tracking/ad-impression   广告曝光
    POST /api/v3/analytics/tracking/ad-click        广告点击

**读聚合（需 ``dashboard:view``）**::

    GET  /api/v3/analytics/tracking/traffic-sources           流量来源
    GET  /api/v3/analytics/tracking/devices                   设备/浏览器/系统分布
    GET  /api/v3/analytics/tracking/popular-pages             热门页面
    GET  /api/v3/analytics/tracking/sessions                  会话统计
    GET  /api/v3/analytics/tracking/articles/{article_id}     单篇文章行为事件
    GET  /api/v3/analytics/tracking/searches                  搜索统计
    GET  /api/v3/analytics/tracking/ads                       广告曝光/点击/CTR

为什么要有这个模块：``page_views`` / ``user_activities`` / ``ad_impressions`` / ``ad_clicks``
四张表在 v3 里**原本没有任何写入点**（表在、模型在、没人写），v2 的那几个 track_* 服务是
唯一写入器且已下线。这里按 v3 规范把写入与读聚合一起补齐，埋点失败不影响业务响应。
"""

from typing import Optional

from fastapi import APIRouter, Query, Request

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, OptionalUser
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.analytics.tracking.schema import (
    AdClickTrackRequest,
    AdImpressionTrackRequest,
    EventTrackRequest,
    PageViewTrackRequest,
    SearchTrackRequest,
)
from src.api.v3.modules.analytics.tracking.service import tracking_service

router = APIRouter(prefix="/tracking", tags=["analytics-tracking"], route_class=OperationLogRoute)


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


# ─────────────────────────── 上报（可选登录）───────────────────────────
@router.post("/page-view", response_model=ResponseModel, summary="上报页面浏览")
async def track_page_view(
    payload: PageViewTrackRequest,
    request: Request,
    db: DBSession,
    user: OptionalUser,
) -> dict:
    data = await tracking_service.record_page_view(
        db,
        page_url=payload.page_url,
        page_title=payload.page_title,
        referrer=payload.referrer,
        session_id=payload.session_id,
        user_id=getattr(user, "id", None),
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return resp.success(data, msg="已记录")


@router.post("/event", response_model=ResponseModel, summary="上报行为事件")
async def track_event(
    payload: EventTrackRequest,
    request: Request,
    db: DBSession,
    user: OptionalUser,
) -> dict:
    data = await tracking_service.record_event(
        db,
        activity_type=payload.activity_type,
        target_type=payload.target_type,
        target_id=payload.target_id,
        details=payload.details,
        user_id=getattr(user, "id", None),
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return resp.success(data, msg="已记录")


@router.post("/search", response_model=ResponseModel, summary="上报搜索记录")
async def track_search(
    payload: SearchTrackRequest,
    db: DBSession,
    user: OptionalUser,
) -> dict:
    data = await tracking_service.record_search(
        db,
        keyword=payload.keyword,
        results_count=payload.results_count,
        user_id=getattr(user, "id", None),
    )
    return resp.success(data, msg="已记录")


@router.post("/ad-impression", response_model=ResponseModel, summary="上报广告曝光")
async def track_ad_impression(
    payload: AdImpressionTrackRequest,
    request: Request,
    db: DBSession,
    user: OptionalUser,
) -> dict:
    data = await tracking_service.record_ad_impression(
        db,
        ad_id=payload.ad_id,
        user_id=getattr(user, "id", None),
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        page_url=payload.page_url,
    )
    return resp.success(data, msg="已记录")


@router.post("/ad-click", response_model=ResponseModel, summary="上报广告点击")
async def track_ad_click(
    payload: AdClickTrackRequest,
    request: Request,
    db: DBSession,
    user: OptionalUser,
) -> dict:
    data = await tracking_service.record_ad_click(
        db,
        ad_id=payload.ad_id,
        user_id=getattr(user, "id", None),
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        referrer=payload.referrer,
    )
    return resp.success(data, msg="已记录")


# ─────────────────────────── 读聚合（需 dashboard:view）───────────────────────────
@router.get("/traffic-sources", response_model=ResponseModel, summary="流量来源（按 referrer 聚合）")
async def traffic_sources(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    days: int = Query(default=7, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    return resp.success(await tracking_service.traffic_sources(db, days=days, limit=limit))


@router.get("/devices", response_model=ResponseModel, summary="设备 / 浏览器 / 系统分布")
async def device_breakdown(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    days: int = Query(default=7, ge=1, le=365),
) -> dict:
    return resp.success(await tracking_service.device_breakdown(db, days=days))


@router.get("/popular-pages", response_model=ResponseModel, summary="热门页面")
async def popular_pages(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    days: int = Query(default=7, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    return resp.success(await tracking_service.popular_pages(db, days=days, limit=limit))


@router.get("/sessions", response_model=ResponseModel, summary="会话统计")
async def session_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    days: int = Query(default=7, ge=1, le=365),
) -> dict:
    return resp.success(await tracking_service.session_stats(db, days=days))


@router.get("/articles/{article_id}", response_model=ResponseModel, summary="单篇文章行为事件统计")
async def article_events(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    return resp.success(await tracking_service.article_events(db, article_id, days=days))


@router.get("/searches", response_model=ResponseModel, summary="搜索统计（热门词 / 零结果率）")
async def search_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    return resp.success(await tracking_service.search_stats(db, days=days, limit=limit))


@router.get("/ads", response_model=ResponseModel, summary="广告曝光 / 点击 / CTR")
async def ad_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DASHBOARD_VIEW),
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    return resp.success(await tracking_service.ad_stats(db, days=days))
