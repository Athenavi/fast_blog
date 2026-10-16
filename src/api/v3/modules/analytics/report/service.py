"""report 模块业务逻辑：真实报表聚合 + 导出 + 定时报表 + 报表历史

**本模块是重写，不是 v2 的平移**。v2 里 `user-activity` / `traffic` / `custom` 三类报表
全部返回硬编码的 0 与空结构，`content` 报表还查了不存在的列
（`articles.view_count`、`article_likes.like_type`）——因此不能"忠实迁移"。这里全部改为
对现有表做**真实聚合**：

  - `content`       ← ``articles`` / ``comments``
  - `user-activity` ← ``users``（注册时间列是 ``date_joined``，不是 ``created_at``）/ ``user_activities``
  - `traffic`       ← ``page_views``（按 ``session_id`` 去重算 UV；按 ``referrer`` 主机归类来源）
  - `engagement`    ← ``article_likes`` / ``comments`` / ``articles``

聚合一律走 SQL（``func.count`` / ``func.sum`` / ``func.date`` / ``func.extract``），
不把全表拉到应用层；只有「按 referrer 分组后的有限几行」在应用层归类求和。

**无法真实计算的指标不会返回占位 0**，而是直接不出现在响应里（例如会话平均时长 ——
``page_views`` 没有时长字段）。导出产出**真实文件**（JSON / CSV + ``Content-Disposition``）。
"""

import csv
import io
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.analytics.page_view import PageView
from shared.models.analytics.user_activity import UserActivity
from shared.models.article.article import Article
from shared.models.article.article_like import ArticleLike
from shared.models.comment.comment import Comment
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.analytics.report.crud import report_history_crud, scheduled_report_crud
from src.api.v3.modules.analytics.report.schema import (
    CUSTOM_METRICS,
    MAX_DAYS,
    MIN_DAYS,
    REPORT_FORMATS,
    REPORT_FREQUENCIES,
    REPORT_TYPES,
    ReportHistoryOut,
    ScheduledReportCreate,
    ScheduledReportOut,
    ScheduledReportUpdate,
)

logger = get_logger("analytics.report")

STATUS_DELETED = -1
STATUS_DRAFT = 0
STATUS_PUBLISHED = 1

#: 报表模板（预置定义，不是"假数据"——它就是模板清单本身）
REPORT_TEMPLATES: list[dict] = [
    {
        "id": "content-overview",
        "name": "内容概览",
        "description": "文章数量、阅读与互动总量，以及阅读排行",
        "report_type": "content",
        "default_days": 30,
    },
    {
        "id": "user-growth",
        "name": "用户活跃",
        "description": "新增 / 活跃 / 回访用户与活跃时段分布",
        "report_type": "user-activity",
        "default_days": 30,
    },
    {
        "id": "traffic-analysis",
        "name": "流量分析",
        "description": "PV / UV、跳出率、来源归类与热门页面",
        "report_type": "traffic",
        "default_days": 30,
    },
    {
        "id": "engagement-metrics",
        "name": "互动指标",
        "description": "点赞 / 评论增量与活跃作者",
        "report_type": "custom",
        "metrics": ["engagement"],
        "default_days": 30,
    },
    {
        "id": "comprehensive",
        "name": "综合报表",
        "description": "内容 + 用户 + 流量 + 互动四块合并",
        "report_type": "custom",
        "metrics": ["content", "users", "traffic", "engagement"],
        "default_days": 30,
    },
]

#: 搜索引擎 / 社交平台的 host 关键字（用于把 referrer 归类）
_SEARCH_HOSTS = ("google.", "bing.", "baidu.", "yahoo.", "duckduckgo", "yandex", "sogou", "so.com")
_SOCIAL_HOSTS = (
    "facebook",
    "twitter",
    "x.com",
    "t.co",
    "weibo",
    "zhihu",
    "reddit",
    "linkedin",
    "instagram",
    "douyin",
    "bilibili",
    "tiktok",
)


def _classify_referrer(referrer: Optional[str]) -> str:
    """把 referrer 归类为 direct / organic_search / social / referral"""
    if not referrer:
        return "direct"
    host = (urlparse(referrer).netloc or "").lower()
    if not host:
        return "direct"
    if any(token in host for token in _SEARCH_HOSTS):
        return "organic_search"
    if any(token in host for token in _SOCIAL_HOSTS):
        return "social"
    return "referral"


def _next_run_at(frequency: str, base: Optional[datetime] = None) -> datetime:
    """下次执行时间：daily=次日 00:00 / weekly=+7 天 00:00 / monthly=下月 1 日 00:00"""
    base = base or datetime.now()
    if frequency == "weekly":
        target = base + timedelta(days=7)
    elif frequency == "monthly":
        year, month = base.year, base.month + 1
        if month > 12:
            year, month = year + 1, 1
        return base.replace(
            year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    else:
        target = base + timedelta(days=1)
    return target.replace(hour=0, minute=0, second=0, microsecond=0)


def _dump_metrics(metrics: Optional[list[str]]) -> Optional[str]:
    return json.dumps(metrics, ensure_ascii=False) if metrics else None


def _scheduled_out(row) -> dict:
    return ScheduledReportOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _history_out(row) -> dict:
    return ReportHistoryOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _clamp_days(days: int) -> int:
    return max(MIN_DAYS, min(int(days), MAX_DAYS))


class ReportService:
    """报表聚合与导出"""

    # ------------------------------------------------------------ 聚合工具
    async def _count(self, db: AsyncSession, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await db.execute(stmt)).scalar() or 0)

    async def _sum(self, db: AsyncSession, column, *conditions) -> int:
        stmt = select(func.coalesce(func.sum(column), 0))
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await db.execute(stmt)).scalar() or 0)

    @staticmethod
    def _since(days: int) -> datetime:
        return datetime.now() - timedelta(days=_clamp_days(days) - 1)

    async def _by_day(self, db: AsyncSession, model, date_column, since: datetime) -> dict[str, int]:
        stmt = (
            select(func.date(date_column).label("day"), func.count())
            .where(date_column >= since)
            .group_by(func.date(date_column))
        )
        return {
            str(day): int(count or 0)
            for day, count in (await db.execute(stmt)).all()
            if day is not None
        }

    # ------------------------------------------------------------ 内容报表
    async def content(self, db: AsyncSession, days: int) -> dict:
        days = _clamp_days(days)
        since = self._since(days)
        active = Article.status != STATUS_DELETED

        total_articles = await self._count(db, Article, active)
        published = await self._count(db, Article, Article.status == STATUS_PUBLISHED)
        total_views = await self._sum(db, Article.views, active)
        total_likes = await self._sum(db, Article.likes, active)
        new_articles = await self._count(db, Article, active, Article.created_at >= since)
        comments_in_period = await self._count(db, Comment, Comment.created_at >= since)
        new_articles_by_day = await self._by_day(db, Article, Article.created_at, since)
        comments_by_day = await self._by_day(db, Comment, Comment.created_at, since)

        top_rows = (
            await db.execute(
                select(Article)
                .where(Article.status == STATUS_PUBLISHED)
                .order_by(Article.views.desc(), Article.id.desc())
                .limit(10)
            )
        ).scalars().all()

        trend = []
        for offset in range(days):
            day = (since + timedelta(days=offset)).date().isoformat()
            trend.append(
                {
                    "day": day,
                    "articles": new_articles_by_day.get(day, 0),
                    "comments": comments_by_day.get(day, 0),
                }
            )

        return {
            "report_type": "content",
            "period": {"start": since, "end": datetime.now(), "days": days},
            "summary": {
                "total_articles": total_articles,
                "published_articles": published,
                "new_articles": new_articles,
                "total_views": total_views,
                "total_likes": total_likes,
                "comments_in_period": comments_in_period,
                "avg_views_per_article": round(total_views / published, 2) if published else 0.0,
            },
            "top_articles": [
                {
                    "id": article.id,
                    "title": article.title,
                    "slug": article.slug,
                    "views": int(article.views or 0),
                    "likes": int(article.likes or 0),
                }
                for article in top_rows
            ],
            "trend": trend,
            "generated_at": datetime.now(),
        }

    # ------------------------------------------------------------ 用户活跃报表
    async def user_activity(self, db: AsyncSession, days: int) -> dict:
        days = _clamp_days(days)
        since = self._since(days)

        total_users = await self._count(db, User)
        new_users = await self._count(db, User, User.date_joined >= since)
        active_total = await self._distinct_active(db, since)
        returning_users = await self._returning_users(db, since)
        new_users_by_day = await self._by_day(db, User, User.date_joined, since)
        active_by_day = await self._active_by_day(db, since)

        hour_rows = (
            await db.execute(
                select(func.extract("hour", UserActivity.created_at).label("h"), func.count())
                .where(UserActivity.created_at >= since)
                .group_by(func.extract("hour", UserActivity.created_at))
            )
        ).all()
        by_hour = {str(hour): 0 for hour in range(24)}
        for hour, count in hour_rows:
            if hour is not None:
                by_hour[str(int(hour))] = int(count or 0)

        weekday_rows = (
            await db.execute(
                select(func.extract("dow", UserActivity.created_at).label("d"), func.count())
                .where(UserActivity.created_at >= since)
                .group_by(func.extract("dow", UserActivity.created_at))
            )
        ).all()
        # dow: 0=周日 … 6=周六
        by_weekday = {str(day): 0 for day in range(7)}
        for day, count in weekday_rows:
            if day is not None:
                by_weekday[str(int(day))] = int(count or 0)

        trend = []
        for offset in range(days):
            day = (since + timedelta(days=offset)).date().isoformat()
            trend.append(
                {
                    "day": day,
                    "new_users": new_users_by_day.get(day, 0),
                    "active_users": active_by_day.get(day, 0),
                }
            )

        return {
            "report_type": "user-activity",
            "period": {"start": since, "end": datetime.now(), "days": days},
            "metrics": {
                "total_users": total_users,
                "new_users": new_users,
                "active_users": active_total,
                "returning_users": returning_users,
                "user_retention_rate": round(active_total / total_users * 100, 2) if total_users else 0.0,
            },
            "activity_distribution": {"by_hour": by_hour, "by_weekday": by_weekday},
            "trend": trend,
            "generated_at": datetime.now(),
        }

    async def _distinct_active(self, db: AsyncSession, since: datetime) -> int:
        stmt = (
            select(func.count(func.distinct(UserActivity.user)))
            .select_from(UserActivity)
            .where(UserActivity.created_at >= since, UserActivity.user.isnot(None))
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def _returning_users(self, db: AsyncSession, since: datetime) -> int:
        """区间内在 **≥2 个不同自然日**都有活动的用户数"""
        grouped = (
            select(UserActivity.user)
            .where(UserActivity.created_at >= since, UserActivity.user.isnot(None))
            .group_by(UserActivity.user)
            .having(func.count(func.distinct(func.date(UserActivity.created_at))) > 1)
            .subquery()
        )
        return int((await db.execute(select(func.count()).select_from(grouped))).scalar() or 0)

    async def _active_by_day(self, db: AsyncSession, since: datetime) -> dict[str, int]:
        stmt = (
            select(func.date(UserActivity.created_at).label("day"), func.count(func.distinct(UserActivity.user)))
            .where(UserActivity.created_at >= since)
            .group_by(func.date(UserActivity.created_at))
        )
        return {
            str(day): int(count or 0)
            for day, count in (await db.execute(stmt)).all()
            if day is not None
        }

    # ------------------------------------------------------------ 流量报表
    async def traffic(self, db: AsyncSession, days: int) -> dict:
        days = _clamp_days(days)
        since = self._since(days)

        total_visits = await self._count(db, PageView, PageView.created_at >= since)
        unique_visitors = int(
            (
                await db.execute(
                    select(func.count(func.distinct(PageView.session_id))).where(
                        PageView.created_at >= since, PageView.session_id.isnot(None)
                    )
                )
            ).scalar()
            or 0
        )

        sessions = (
            select(PageView.session_id.label("sid"), func.count().label("views"))
            .where(PageView.created_at >= since, PageView.session_id.isnot(None))
            .group_by(PageView.session_id)
        ).subquery()
        total_sessions = int(
            (await db.execute(select(func.count()).select_from(sessions))).scalar() or 0
        )
        single_view_sessions = int(
            (
                await db.execute(
                    select(func.count()).select_from(sessions).where(sessions.c.views == 1)
                )
            ).scalar()
            or 0
        )
        bounce_rate = round(single_view_sessions / total_sessions * 100, 2) if total_sessions else 0.0

        referrer_rows = (
            await db.execute(
                select(PageView.referrer, func.count())
                .where(PageView.created_at >= since)
                .group_by(PageView.referrer)
            )
        ).all()
        sources = {"direct": 0, "organic_search": 0, "social": 0, "referral": 0}
        for referrer, count in referrer_rows:
            sources[_classify_referrer(referrer)] += int(count or 0)

        top_pages = (
            await db.execute(
                select(PageView.page_url, func.count().label("views"))
                .where(PageView.created_at >= since, PageView.page_url.isnot(None))
                .group_by(PageView.page_url)
                .order_by(func.count().desc())
                .limit(10)
            )
        ).all()

        pv_by_day = await self._by_day(db, PageView, PageView.created_at, since)
        uv_rows = (
            await db.execute(
                select(
                    func.date(PageView.created_at).label("day"),
                    func.count(func.distinct(PageView.session_id)),
                )
                .where(PageView.created_at >= since, PageView.session_id.isnot(None))
                .group_by(func.date(PageView.created_at))
            )
        ).all()
        uv_by_day = {str(day): int(count or 0) for day, count in uv_rows if day is not None}

        trend = []
        for offset in range(days):
            day = (since + timedelta(days=offset)).date().isoformat()
            trend.append(
                {
                    "day": day,
                    "page_views": pv_by_day.get(day, 0),
                    "unique_visitors": uv_by_day.get(day, 0),
                }
            )

        return {
            "report_type": "traffic",
            "period": {"start": since, "end": datetime.now(), "days": days},
            # 注：``avg_session_duration`` 无法真实计算（page_views 没有时长字段），
            # 因此**不返回该字段**，而不是给一个占位的 0
            "overview": {
                "total_visits": total_visits,
                "unique_visitors": unique_visitors,
                "total_sessions": total_sessions,
                "bounce_rate": bounce_rate,
            },
            "sources": sources,
            "top_pages": [
                {"page_url": url, "views": int(count or 0)} for url, count in top_pages
            ],
            "trend": trend,
            "generated_at": datetime.now(),
        }

    # ------------------------------------------------------------ 互动报表
    async def engagement(self, db: AsyncSession, days: int) -> dict:
        days = _clamp_days(days)
        since = self._since(days)

        likes = await self._count(db, ArticleLike, ArticleLike.created_at >= since)
        comments = await self._count(db, Comment, Comment.created_at >= since)
        new_articles = await self._count(
            db, Article, Article.created_at >= since, Article.status != STATUS_DELETED
        )
        active_authors = int(
            (
                await db.execute(
                    select(func.count(func.distinct(Article.user))).where(
                        Article.created_at >= since,
                        Article.status != STATUS_DELETED,
                        Article.user.isnot(None),
                    )
                )
            ).scalar()
            or 0
        )
        likes_by_day = await self._by_day(db, ArticleLike, ArticleLike.created_at, since)
        comments_by_day = await self._by_day(db, Comment, Comment.created_at, since)

        trend = []
        for offset in range(days):
            day = (since + timedelta(days=offset)).date().isoformat()
            trend.append(
                {
                    "day": day,
                    "likes": likes_by_day.get(day, 0),
                    "comments": comments_by_day.get(day, 0),
                }
            )

        return {
            "report_type": "engagement",
            "period": {"start": since, "end": datetime.now(), "days": days},
            "metrics": {
                "likes_in_period": likes,
                "comments_in_period": comments,
                "new_articles": new_articles,
                "active_authors": active_authors,
                "avg_interactions_per_article": (
                    round((likes + comments) / new_articles, 2) if new_articles else 0.0
                ),
            },
            "trend": trend,
            "generated_at": datetime.now(),
        }

    # ------------------------------------------------------------ 统一入口
    async def build(
        self,
        db: AsyncSession,
        *,
        report_type: str,
        days: int = 30,
        metrics: Optional[list[str]] = None,
        filters: Optional[dict] = None,
    ) -> dict:
        if report_type not in REPORT_TYPES:
            raise BadRequestError(
                f"报表类型不合法: {report_type}（可选 {'/'.join(REPORT_TYPES)}）"
            )
        if report_type == "content":
            return await self.content(db, days)
        if report_type == "user-activity":
            return await self.user_activity(db, days)
        if report_type == "traffic":
            return await self.traffic(db, days)
        return await self.custom(db, metrics=metrics, days=days, filters=filters)

    async def custom(
        self,
        db: AsyncSession,
        *,
        metrics: Optional[list[str]],
        days: int,
        filters: Optional[dict] = None,
    ) -> dict:
        if not metrics:
            raise BadRequestError("自定义报表必须指定 metrics")
        invalid = [item for item in metrics if item not in CUSTOM_METRICS]
        if invalid:
            raise BadRequestError(
                f"无效的指标: {'/'.join(invalid)}（可选 {'/'.join(CUSTOM_METRICS)}）"
            )
        requested = list(dict.fromkeys(metrics))
        blocks: dict[str, Any] = {}
        for metric in requested:
            if metric == "content":
                blocks["content"] = (await self.content(db, days))["summary"]
            elif metric == "users":
                blocks["users"] = (await self.user_activity(db, days))["metrics"]
            elif metric == "traffic":
                blocks["traffic"] = (await self.traffic(db, days))["overview"]
            else:
                blocks["engagement"] = (await self.engagement(db, days))["metrics"]
        return {
            "report_type": "custom",
            "period": {
                "start": self._since(days),
                "end": datetime.now(),
                "days": _clamp_days(days),
            },
            "metrics": blocks,
            "requested_metrics": requested,
            "filters": filters,
            "generated_at": datetime.now(),
        }

    # ------------------------------------------------------------ 导出
    @staticmethod
    def render(payload: dict, fmt: str) -> tuple[str, str, str]:
        """把报表 dict 渲染成可下载内容，返回 ``(content, media_type, extension)``"""
        if fmt not in REPORT_FORMATS:
            raise BadRequestError(f"导出格式不合法: {fmt}（可选 {'/'.join(REPORT_FORMATS)}）")
        if fmt == "json":
            return json.dumps(payload, ensure_ascii=False, indent=2, default=str), "application/json", "json"
        return ReportService._to_csv(payload), "text/csv; charset=utf-8", "csv"

    @staticmethod
    def _to_csv(payload: dict) -> str:
        """把嵌套报表扁平化成 ``指标,值`` 两列（列表展开为 ``path[0].field``）"""
        rows: list[tuple[str, str]] = []

        def walk(prefix: str, value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    walk(f"{prefix}.{key}" if prefix else str(key), item)
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, dict):
                        for key, sub in item.items():
                            walk(f"{prefix}[{index}].{key}", sub)
                    else:
                        rows.append((f"{prefix}[{index}]", "" if item is None else str(item)))
            else:
                rows.append((prefix, "" if value is None else str(value)))

        walk("", payload)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)
        return buffer.getvalue()

    # ------------------------------------------------------------ 定时报表
    async def list_scheduled(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        report_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await scheduled_report_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"report_type": report_type, "is_active": is_active},
        )
        return [_scheduled_out(row) for row in rows], total

    async def create_scheduled(self, db: AsyncSession, payload: ScheduledReportCreate) -> dict:
        if payload.report_type not in REPORT_TYPES:
            raise BadRequestError(f"报表类型不合法: {payload.report_type}")
        if payload.frequency not in REPORT_FREQUENCIES:
            raise BadRequestError(f"执行频率不合法: {payload.frequency}")
        if payload.export_format not in REPORT_FORMATS:
            raise BadRequestError(f"导出格式不合法: {payload.export_format}")
        if payload.report_type == "custom" and not payload.metrics:
            raise BadRequestError("自定义报表必须指定 metrics")
        now = datetime.now()
        row = await scheduled_report_crud.create(
            db,
            payload.model_dump(exclude={"metrics", "name", "report_type", "frequency"})
            | {
                "name": payload.name,
                "report_type": payload.report_type,
                "frequency": payload.frequency,
                "metrics": _dump_metrics(payload.metrics),
                "next_run_at": _next_run_at(payload.frequency, now),
                "created_at": now,
                "updated_at": now,
            },
        )
        return _scheduled_out(row)

    async def update_scheduled(
        self, db: AsyncSession, report_id: int, payload: ScheduledReportUpdate
    ) -> dict:
        row = await scheduled_report_crud.get(db, report_id)
        if row is None:
            raise NotFoundError("定时报表不存在")
        data = payload.model_dump(exclude_unset=True)
        if "report_type" in data and data["report_type"] not in REPORT_TYPES:
            raise BadRequestError(f"报表类型不合法: {data['report_type']}")
        if "frequency" in data and data["frequency"] not in REPORT_FREQUENCIES:
            raise BadRequestError(f"执行频率不合法: {data['frequency']}")
        if "export_format" in data and data["export_format"] not in REPORT_FORMATS:
            raise BadRequestError(f"导出格式不合法: {data['export_format']}")
        if "metrics" in data:
            data["metrics"] = _dump_metrics(data.pop("metrics"))
        if "frequency" in data:
            data["next_run_at"] = _next_run_at(data["frequency"])
        updated = await scheduled_report_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _scheduled_out(updated)

    async def delete_scheduled(self, db: AsyncSession, report_id: int) -> None:
        row = await scheduled_report_crud.get(db, report_id)
        if row is None:
            raise NotFoundError("定时报表不存在")
        await scheduled_report_crud.remove(db, row)

    async def toggle_scheduled(self, db: AsyncSession, report_id: int) -> dict:
        row = await scheduled_report_crud.get(db, report_id)
        if row is None:
            raise NotFoundError("定时报表不存在")
        data: dict = {"is_active": not bool(row.is_active), "updated_at": datetime.now()}
        if data["is_active"]:
            # 重新激活时把下次执行时间顺延到下一个周期
            data["next_run_at"] = _next_run_at(row.frequency or "daily")
        updated = await scheduled_report_crud.update(db, row, data)
        return _scheduled_out(updated)

    async def run_scheduled(self, db: AsyncSession, report_id: int) -> dict:
        """立即执行一次：生成报表 → **真实写入** ``report_history`` → 顺延 ``next_run_at``"""
        row = await scheduled_report_crud.get(db, report_id)
        if row is None:
            raise NotFoundError("定时报表不存在")
        metrics = None
        if row.metrics:
            try:
                parsed = json.loads(row.metrics)
                metrics = parsed if isinstance(parsed, list) else None
            except ValueError:
                metrics = None
        report = await self.build(
            db, report_type=row.report_type or "content", days=row.days or 30, metrics=metrics
        )
        fmt = row.export_format or "json"
        content, _media_type, _ext = self.render(report, fmt)
        now = datetime.now()
        history = await report_history_crud.create(
            db,
            {
                "scheduled_report_id": row.id,
                "report_name": row.name or f"{row.report_type}-{row.id}",
                "report_type": row.report_type,
                "content": content,
                "format": fmt,
                "generated_at": now,
            },
        )
        await scheduled_report_crud.update(
            db,
            row,
            {
                "last_run_at": now,
                "next_run_at": _next_run_at(row.frequency or "daily", now),
                "updated_at": now,
            },
        )
        return _history_out(history)

    # ------------------------------------------------------------ 报表历史
    async def list_history(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        report_type: Optional[str] = None,
        scheduled_report_id: Optional[int] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await report_history_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"report_type": report_type, "scheduled_report_id": scheduled_report_id},
        )
        return [_history_out(row) for row in rows], total

    async def get_history_row(self, db: AsyncSession, history_id: int):
        row = await report_history_crud.get(db, history_id)
        if row is None:
            raise NotFoundError("报表历史不存在")
        return row


report_service = ReportService()
