"""seo 模块路由

::

    POST /api/v3/analytics/seo/analyze                    对任意内容做 SEO 分析（编辑器实时提示）
    GET  /api/v3/analytics/seo/articles/{article_id}      单篇文章 SEO 分析
    POST /api/v3/analytics/seo/bulk-check                 批量检查（按 id 或全部已发布）
    GET  /api/v3/analytics/seo/keywords                   关键词统计
    GET  /api/v3/analytics/seo/orphan-articles            孤立文章（无入链）
    GET  /api/v3/analytics/seo/link-distribution          内链分布
    GET  /api/v3/analytics/seo/internal-links/{article_id} 内链建议
    GET  /api/v3/analytics/seo/report                     综合报告

权限码：``settings:view``（分析与报告）/ ``article:view``（文章维度）/ ``article:edit``（编辑器分析）
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.modules.analytics.seo.schema import BulkCheckRequest, SEOAnalyzeRequest
from src.api.v3.modules.analytics.seo.service import seo_service

router = APIRouter(prefix="/seo", tags=["analytics-seo"])


@router.post("/analyze", response_model=ResponseModel, summary="分析任意内容（不落库）")
async def analyze_content(
    payload: SEOAnalyzeRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_EDIT),
) -> dict:
    return resp.success(await seo_service.analyze_content(payload))


@router.get("/keywords", response_model=ResponseModel, summary="关键词统计")
async def keywords(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_VIEW),
    limit: int = Query(default=50, ge=1, le=500),
    scan_limit: int = Query(default=300, ge=1, le=1000, description="参与统计的文章篇数上限"),
) -> dict:
    return resp.success(await seo_service.keywords(db, limit=limit, scan_limit=scan_limit))


@router.get("/orphan-articles", response_model=ResponseModel, summary="孤立文章（无入链）")
async def orphan_articles(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_VIEW),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    return resp.success(await seo_service.orphan_articles(db, limit=limit))


@router.get("/link-distribution", response_model=ResponseModel, summary="内链分布")
async def link_distribution(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_VIEW),
) -> dict:
    return resp.success(await seo_service.link_distribution(db))


@router.get("/report", response_model=ResponseModel, summary="综合 SEO 报告")
async def seo_report(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_VIEW),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    return resp.success(await seo_service.report(db, limit=limit))


@router.post("/bulk-check", response_model=ResponseModel, summary="批量 SEO 检查")
async def bulk_check(
    payload: BulkCheckRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_EDIT),
) -> dict:
    return resp.success(await seo_service.bulk_check(db, payload))


@router.get("/articles/{article_id}", response_model=ResponseModel, summary="单篇文章 SEO 分析")
async def analyze_article(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_VIEW),
) -> dict:
    return resp.success(await seo_service.analyze_article(db, article_id))


@router.get(
    "/internal-links/{article_id}",
    response_model=ResponseModel,
    summary="内链建议",
)
async def internal_link_suggestions(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_VIEW),
) -> dict:
    return resp.success(await seo_service.internal_link_suggestions(db, article_id))
