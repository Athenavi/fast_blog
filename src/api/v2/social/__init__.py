"""
分享统计 API - V2 原生实现

提供分享追踪、按平台统计、文章排行功能
优化: 提取重复校验逻辑，统一错误处理
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article
from shared.models.social import ShareStat
from src.api.v2._base import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session

_router = None


async def _require_article(db: AsyncSession, article_id: int) -> Optional[ApiResponse]:
    """校验文章存在，不存在返回错误响应"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        return ApiResponse(success=False, error="文章不存在")
    return None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["social"])

    @router.post("/shares/track")
    async def track_share(
            article_id: int = Query(..., description="文章ID"),
            platform: str = Query(...,
                                  description="分享平台: wechat/weibo/twitter/facebook/linkedin/zhihu/juejin/segmentfault/telegram/copy"),
            request: Request = None,
            current_user_id: Optional[int] = Depends(jwt_required),
            db: AsyncSession = Depends(get_async_session)
    ):
        """记录分享行为"""
        err = await _require_article(db, article_id)
        if err:
            return err

        ip_address = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None

        db.add(ShareStat(
            article_id=article_id, platform=platform,
            shared_by=current_user_id,
            ip_address=ip_address, user_agent=user_agent,
            created_at=datetime.now()
        ))
        await db.commit()
        return ApiResponse(success=True, message="分享记录成功")

    @router.get("/shares/stats/{article_id}")
    async def get_article_share_stats(
            article_id: int,
            days: int = Query(30, ge=1, le=365, description="统计天数"),
            db: AsyncSession = Depends(get_async_session)
    ):
        """获取文章分享统计（按平台分布 + 每日趋势）"""
        err = await _require_article(db, article_id)
        if err:
            return err

        cutoff = datetime.now() - timedelta(days=days)

        total = await db.scalar(
            select(func.count()).select_from(ShareStat).where(
                ShareStat.article_id == article_id, ShareStat.created_at >= cutoff)
        ) or 0

        rows = (await db.execute(
            select(ShareStat.platform, func.count().label('c'))
            .where(ShareStat.article_id == article_id, ShareStat.created_at >= cutoff)
            .group_by(ShareStat.platform).order_by(desc('c'))
        )).all()
        by_platform = [{"platform": r.platform, "count": r.c} for r in rows]

        trend_rows = (await db.execute(
            select(func.date(ShareStat.created_at).label('d'), func.count().label('c'))
            .where(ShareStat.article_id == article_id, ShareStat.created_at >= cutoff)
            .group_by(func.date(ShareStat.created_at)).order_by(desc('d'))
        )).all()
        trend = [{"date": r.d.isoformat(), "count": r.c} for r in trend_rows]
        trend.reverse()

        return ApiResponse(success=True, data={
            "article_id": article_id, "total_shares": total,
            "period_days": days, "by_platform": by_platform, "trend": trend,
        })

    @router.get("/shares/ranking")
    async def get_share_ranking(
            days: int = Query(7, ge=1, le=365, description="统计天数"),
            limit: int = Query(10, ge=1, le=100, description="返回数量"),
            db: AsyncSession = Depends(get_async_session)
    ):
        """热门文章分享排行"""
        cutoff = datetime.now() - timedelta(days=days)
        rows = (await db.execute(
            select(ShareStat.article_id, Article.title, Article.slug, func.count().label('sc'))
            .join(Article, ShareStat.article_id == Article.id)
            .where(ShareStat.created_at >= cutoff, Article.status == 1)
            .group_by(ShareStat.article_id, Article.title, Article.slug)
            .order_by(desc('sc')).limit(limit)
        )).all()
        return ApiResponse(success=True, data={
            "period_days": days,
            "ranking": [{"article_id": r.article_id, "title": r.title, "slug": r.slug, "share_count": r.sc} for r in rows]
        })

    @router.get("/shares/platform-stats")
    async def get_platform_statistics(
            days: int = Query(30, ge=1, le=365, description="统计天数"),
            db: AsyncSession = Depends(get_async_session)
    ):
        """各分享平台总体统计"""
        cutoff = datetime.now() - timedelta(days=days)
        rows = (await db.execute(
            select(ShareStat.platform, func.count().label('c'),
                   func.count(func.distinct(ShareStat.article_id)).label('ua'))
            .where(ShareStat.created_at >= cutoff)
            .group_by(ShareStat.platform).order_by(desc('c'))
        )).all()
        total = await db.scalar(
            select(func.count()).select_from(ShareStat).where(ShareStat.created_at >= cutoff)
        ) or 0
        return ApiResponse(success=True, data={
            "period_days": days, "total_shares": total,
            "by_platform": [{"platform": r.platform, "total_shares": r.c, "unique_articles": r.ua} for r in rows]
        })

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
