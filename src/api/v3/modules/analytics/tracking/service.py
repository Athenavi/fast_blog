"""埋点写入（真实落库，激活 v2 遗留的 4 张"死表"）

背景：``page_views`` / ``user_activities`` / ``ad_impressions`` / ``ad_clicks`` 四张表在
v3 里**没有任何写入点**（表在、模型在、就是没人写），而 v2 的
``shared/services/{analytics/site_analytics,analytics/content_analytics,
marketing/advertisement_system,articles/*}`` 是唯一的写入器。本模块把那套能力按 v3 规范
重做：**真实写表 + UA 轻量解析 + 读侧聚合**（读侧见同目录 ``service`` 的查询方法）。

设计取舍：

  - 不做第三方 UA 解析依赖：用轻量正则识别设备/浏览器/系统（埋点在热路径上，避免引库）
  - 写入失败**不影响业务**：调用方（文章浏览量 +1 等）把它当成 best-effort，
    但方法本身会抛异常，由调用方决定是否吞掉
  - ``session_id`` 由前端生成并复用（同一会话的多次浏览共享），便于聚合会话统计
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.ad.ad import Ad
from shared.models.ad.ad_click import AdClick
from shared.models.ad.ad_impression import AdImpression
from shared.models.analytics.page_view import PageView
from shared.models.analytics.user_activity import UserActivity
from shared.models.search.search_history import SearchHistory
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("analytics.tracking")

#: 明细字段长度上限（与模型列宽一致，避免写库报错）
MAX_URL = 500
MAX_TITLE = 500
MAX_REFERRER = 500
MAX_UA = 500
MAX_ACTIVITY_TYPE = 100
MAX_TARGET_TYPE = 50
MAX_DETAILS = 255
MAX_KEYWORD = 255

_MOBILE_RE = re.compile(r"(android|iphone|ipod|windows phone|mobile)", re.I)
_TABLET_RE = re.compile(r"(ipad|tablet|kindle|playbook|silk)", re.I)
#: 顺序即优先级：越专用的规则越靠前（微信/百度 UA 里同样带 Chrome/Safari 片段）
_BROWSERS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("Bot", re.compile(r"bot|crawler|spider|curl|wget|python-requests", re.I)),
    ("WeChat", re.compile(r"micromessenger", re.I)),
    ("Baidu", re.compile(r"baiduboxapp|baidubrowser", re.I)),
    ("Edg", re.compile(r"edg/", re.I)),
    ("Opera", re.compile(r"opr/|opera", re.I)),
    ("Chrome", re.compile(r"chrome/|crios/", re.I)),
    ("Firefox", re.compile(r"firefox/|fxios/", re.I)),
    ("Safari", re.compile(r"safari/", re.I)),
)
_PLATFORMS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("Windows", re.compile(r"windows", re.I)),
    ("iOS", re.compile(r"iphone|ipad|ipod", re.I)),
    ("Android", re.compile(r"android", re.I)),
    ("macOS", re.compile(r"mac os x|macintosh", re.I)),
    ("Linux", re.compile(r"linux", re.I)),
)


def parse_user_agent(ua: Optional[str]) -> Dict[str, Optional[str]]:
    """轻量 UA 解析：设备类型 / 浏览器 / 操作系统（识别不到就返回 None）"""
    text = (ua or "").strip()
    if not text:
        return {"device_type": None, "browser": None, "platform": None}

    if _TABLET_RE.search(text):
        device = "tablet"
    elif _MOBILE_RE.search(text):
        device = "mobile"
    else:
        device = "desktop"

    browser = next((name for name, pattern in _BROWSERS if pattern.search(text)), None)
    platform = next((name for name, pattern in _PLATFORMS if pattern.search(text)), None)
    return {"device_type": device, "browser": browser, "platform": platform}


def _trim(value: Optional[str], limit: int) -> Optional[str]:
    if value is None:
        return None
    return value[:limit]


class TrackingService:
    """埋点写入 + 读侧聚合（全部基于真表）"""

    @staticmethod
    async def _assert_ad_exists(db: AsyncSession, ad_id: int) -> None:
        """广告必须存在：直接插入会因外键违反抛 500，这里转成明确的 404"""
        exists = await db.scalar(select(Ad.id).where(Ad.id == ad_id))
        if exists is None:
            raise NotFoundError(f"广告 {ad_id} 不存在")

    # ------------------------------------------------------------------ 写入
    async def record_page_view(
        self,
        db: AsyncSession,
        *,
        page_url: str,
        page_title: Optional[str] = None,
        referrer: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        country: Optional[str] = None,
        city: Optional[str] = None,
    ) -> Dict[str, Any]:
        """记录一次页面浏览（写 ``page_views``，含 UA 解析结果）"""
        parsed = parse_user_agent(user_agent)
        row = PageView(
            user=user_id,
            session_id=_trim(session_id, 255),
            page_url=_trim(page_url, MAX_URL),
            page_title=_trim(page_title, MAX_TITLE),
            referrer=_trim(referrer, MAX_REFERRER),
            user_agent=_trim(user_agent, MAX_UA),
            ip_address=_trim(ip_address, 45),
            device_type=parsed["device_type"],
            browser=parsed["browser"],
            platform=parsed["platform"],
            country=_trim(country, 100),
            city=_trim(city, 100),
            created_at=datetime.now(),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return {"id": row.id, "device_type": row.device_type, "browser": row.browser, "platform": row.platform}

    async def record_event(
        self,
        db: AsyncSession,
        *,
        activity_type: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        details: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """记录一次用户行为事件（写 ``user_activities``）

        ``activity_type`` 建议使用稳定枚举：``view`` / ``like`` / ``unlike`` / ``share`` /
        ``bookmark`` / ``comment`` / ``click`` / ``scroll`` / ``search`` / ``follow`` / ``purchase``。
        """
        row = UserActivity(
            user=user_id,
            activity_type=_trim(activity_type, MAX_ACTIVITY_TYPE),
            target_type=_trim(target_type, MAX_TARGET_TYPE),
            target_id=target_id,
            details=_trim(details, MAX_DETAILS),
            ip_address=_trim(ip_address, 45),
            user_agent=_trim(user_agent, MAX_UA),
            created_at=datetime.now(),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return {"id": row.id, "activity_type": row.activity_type}

    async def record_search(
        self,
        db: AsyncSession,
        *,
        keyword: str,
        results_count: int = 0,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """记录一次搜索（写 ``search_history``，用于热门词与零结果率）"""
        row = SearchHistory(
            user=user_id,
            keyword=_trim(keyword, MAX_KEYWORD),
            results_count=int(results_count or 0),
            created_at=datetime.now(),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return {"id": row.id, "keyword": row.keyword}

    async def record_ad_impression(
        self,
        db: AsyncSession,
        *,
        ad_id: int,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        page_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """记录广告曝光（写 ``ad_impressions``）"""
        await self._assert_ad_exists(db, ad_id)
        row = AdImpression(
            ad_id=ad_id,
            user_id=user_id,
            ip_address=_trim(ip_address, 45),
            user_agent=_trim(user_agent, 1024),
            page_url=_trim(page_url, MAX_URL),
            displayed_at=datetime.now(),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return {"id": row.id, "ad_id": row.ad_id}

    async def record_ad_click(
        self,
        db: AsyncSession,
        *,
        ad_id: int,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """记录广告点击（写 ``ad_clicks``）"""
        await self._assert_ad_exists(db, ad_id)
        row = AdClick(
            ad_id=ad_id,
            user_id=user_id,
            ip_address=_trim(ip_address, 45),
            user_agent=_trim(user_agent, 1024),
            referrer=_trim(referrer, MAX_REFERRER),
            clicked_at=datetime.now(),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return {"id": row.id, "ad_id": row.ad_id}

    # ------------------------------------------------------------------ 读聚合
    async def traffic_sources(
        self, db: AsyncSession, *, days: int = 7, limit: int = 20
    ) -> Dict[str, Any]:
        """流量来源（按 ``referrer`` 聚合；空 referrer 归为"直接访问"）"""
        since = datetime.now() - timedelta(days=days)
        source = func.coalesce(PageView.referrer, "")
        rows = (
            await db.execute(
                select(source.label("source"), func.count().label("views"))
                .where(PageView.created_at >= since)
                .group_by(source)
                .order_by(func.count().desc())
                .limit(limit)
            )
        ).all()
        total = sum(int(row.views) for row in rows) or 1
        return {
            "period_days": days,
            "total": sum(int(row.views) for row in rows),
            "items": [
                {
                    "source": row.source or "(direct)",
                    "views": int(row.views),
                    "share": round(int(row.views) / total, 4),
                }
                for row in rows
            ],
        }

    async def device_breakdown(self, db: AsyncSession, *, days: int = 7) -> Dict[str, Any]:
        """设备 / 浏览器 / 系统分布（来自 ``page_views`` 的 UA 解析结果）"""
        since = datetime.now() - timedelta(days=days)

        async def _group(column) -> List[Dict[str, Any]]:
            rows = (
                await db.execute(
                    select(column, func.count().label("views"))
                    .where(PageView.created_at >= since)
                    .group_by(column)
                    .order_by(func.count().desc())
                )
            ).all()
            return [
                {"name": row[0] or "unknown", "views": int(row[1])}
                for row in rows
            ]

        return {
            "period_days": days,
            "device_type": await _group(PageView.device_type),
            "browser": await _group(PageView.browser),
            "platform": await _group(PageView.platform),
        }

    async def popular_pages(
        self, db: AsyncSession, *, days: int = 7, limit: int = 20
    ) -> Dict[str, Any]:
        """热门页面（``page_views`` 按 URL 聚合，含独立会话数）"""
        since = datetime.now() - timedelta(days=days)
        rows = (
            await db.execute(
                select(
                    PageView.page_url,
                    func.count().label("views"),
                    func.count(func.distinct(PageView.session_id)).label("sessions"),
                )
                .where(PageView.created_at >= since, PageView.page_url.is_not(None))
                .group_by(PageView.page_url)
                .order_by(func.count().desc())
                .limit(limit)
            )
        ).all()
        return {
            "period_days": days,
            "items": [
                {
                    "page_url": row.page_url,
                    "views": int(row.views),
                    "sessions": int(row.sessions or 0),
                }
                for row in rows
            ],
        }

    async def session_stats(self, db: AsyncSession, *, days: int = 7) -> Dict[str, Any]:
        """会话统计（``page_views`` 按 session_id 聚合：会话数、人均浏览、单会话峰值）"""
        since = datetime.now() - timedelta(days=days)
        per_session = (
            select(PageView.session_id, func.count().label("views"))
            .where(PageView.created_at >= since, PageView.session_id.is_not(None))
            .group_by(PageView.session_id)
            .subquery()
        )
        row = (
            await db.execute(
                select(
                    func.count().label("sessions"),
                    func.avg(per_session.c.views).label("avg_views"),
                    func.max(per_session.c.views).label("max_views"),
                ).select_from(per_session)
            )
        ).one()
        sessions = int(row.sessions or 0)
        return {
            "period_days": days,
            "sessions": sessions,
            "avg_views_per_session": round(float(row.avg_views or 0), 2),
            "max_views_in_session": int(row.max_views or 0),
        }

    async def article_events(
        self, db: AsyncSession, article_id: int, *, days: int = 30
    ) -> Dict[str, Any]:
        """单篇文章的行为事件统计（``user_activities`` 里 target_type='article'）"""
        since = datetime.now() - timedelta(days=days)
        rows = (
            await db.execute(
                select(UserActivity.activity_type, func.count().label("count"))
                .where(
                    UserActivity.created_at >= since,
                    UserActivity.target_type == "article",
                    UserActivity.target_id == article_id,
                )
                .group_by(UserActivity.activity_type)
                .order_by(func.count().desc())
            )
        ).all()
        by_type = {row.activity_type or "unknown": int(row.count) for row in rows}
        return {
            "article_id": article_id,
            "period_days": days,
            "by_type": by_type,
            "total": sum(by_type.values()),
        }

    async def search_stats(
        self, db: AsyncSession, *, days: int = 30, limit: int = 20
    ) -> Dict[str, Any]:
        """搜索统计：热门关键词、零结果关键词、零结果率"""
        since = datetime.now() - timedelta(days=days)
        rows = (
            await db.execute(
                select(
                    SearchHistory.keyword,
                    func.count().label("count"),
                    func.avg(SearchHistory.results_count).label("avg_results"),
                )
                .where(SearchHistory.created_at >= since, SearchHistory.keyword.is_not(None))
                .group_by(SearchHistory.keyword)
                .order_by(func.count().desc())
                .limit(limit)
            )
        ).all()
        total = (
                    await db.execute(
                        select(func.count()).select_from(SearchHistory).where(SearchHistory.created_at >= since)
                    )
                ).scalar() or 0
        zero = (
                   await db.execute(
                       select(func.count())
                       .select_from(SearchHistory)
                       .where(SearchHistory.created_at >= since, SearchHistory.results_count == 0)
                   )
               ).scalar() or 0
        return {
            "period_days": days,
            "total_searches": int(total),
            "zero_result_rate": round(int(zero) / int(total), 4) if total else 0.0,
            "items": [
                {
                    "keyword": row.keyword,
                    "count": int(row.count),
                    "avg_results": round(float(row.avg_results or 0), 2),
                }
                for row in rows
            ],
        }

    async def ad_stats(self, db: AsyncSession, *, days: int = 30) -> Dict[str, Any]:
        """广告曝光/点击/点击率（真表聚合，供广告看板）"""
        since = datetime.now() - timedelta(days=days)
        impressions = (
                          await db.execute(
                              select(func.count()).select_from(AdImpression).where(AdImpression.displayed_at >= since)
                          )
                      ).scalar() or 0
        clicks = (
                     await db.execute(
                         select(func.count()).select_from(AdClick).where(AdClick.clicked_at >= since)
                     )
                 ).scalar() or 0
        per_ad = (
            await db.execute(
                select(AdClick.ad_id, func.count().label("clicks"))
                .where(AdClick.clicked_at >= since)
                .group_by(AdClick.ad_id)
                .order_by(func.count().desc())
                .limit(10)
            )
        ).all()
        return {
            "period_days": days,
            "impressions": int(impressions),
            "clicks": int(clicks),
            "ctr": round(int(clicks) / int(impressions), 4) if impressions else 0.0,
            "top_ads": [{"ad_id": row.ad_id, "clicks": int(row.clicks)} for row in per_ad],
        }


tracking_service = TrackingService()
