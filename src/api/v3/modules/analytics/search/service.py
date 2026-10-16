"""search_analytics 模块业务逻辑

全部走 ``search_history`` 的聚合查询；关键词去重与排名在数据库侧完成。
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.search.search_history import SearchHistory
from src.api.v3.core.logger import get_logger

logger = get_logger("search_analytics")

MAX_DAYS = 365
MAX_LIMIT = 200


class SearchAnalyticsService:
    """搜索行为分析"""

    def _since(self, days: Optional[int]) -> Optional[datetime]:
        if not days:
            return None
        days = max(1, min(int(days), MAX_DAYS))
        return datetime.now() - timedelta(days=days)

    async def summary(self, db: AsyncSession, *, days: Optional[int] = None) -> dict:
        since = self._since(days)
        base = select(func.count()).select_from(SearchHistory)
        if since is not None:
            base = base.where(SearchHistory.created_at >= since)
        total = int((await db.execute(base)).scalar() or 0)

        unique_stmt = select(func.count(func.distinct(SearchHistory.keyword)))
        zero_stmt = select(func.count()).select_from(SearchHistory).where(
            SearchHistory.results_count == 0
        )
        if since is not None:
            unique_stmt = unique_stmt.where(SearchHistory.created_at >= since)
            zero_stmt = zero_stmt.where(SearchHistory.created_at >= since)

        unique = int((await db.execute(unique_stmt)).scalar() or 0)
        zero = int((await db.execute(zero_stmt)).scalar() or 0)

        return {
            "total_searches": total,
            "unique_keywords": unique,
            "zero_result_searches": zero,
            "zero_result_rate": round(zero / total, 4) if total else None,
        }

    async def popular(
        self, db: AsyncSession, *, limit: int = 20, days: Optional[int] = None
    ) -> List[dict]:
        since = self._since(days)
        stmt = select(
            SearchHistory.keyword.label("keyword"),
            func.count().label("count"),
            func.avg(SearchHistory.results_count).label("avg_results"),
        )
        if since is not None:
            stmt = stmt.where(SearchHistory.created_at >= since)
        stmt = (
            stmt.group_by(SearchHistory.keyword)
            .order_by(func.count().desc())
            .limit(max(1, min(limit, MAX_LIMIT)))
        )
        return [
            {
                "keyword": keyword,
                "count": int(count or 0),
                "avg_results": round(float(avg or 0), 2),
            }
            for keyword, count, avg in (await db.execute(stmt)).all()
        ]

    async def zero_result(
        self, db: AsyncSession, *, limit: int = 20, days: Optional[int] = None
    ) -> List[dict]:
        since = self._since(days)
        stmt = select(SearchHistory.keyword.label("keyword"), func.count().label("count")).where(
            SearchHistory.results_count == 0
        )
        if since is not None:
            stmt = stmt.where(SearchHistory.created_at >= since)
        stmt = (
            stmt.group_by(SearchHistory.keyword)
            .order_by(func.count().desc())
            .limit(max(1, min(limit, MAX_LIMIT)))
        )
        return [
            {"keyword": keyword, "count": int(count or 0)}
            for keyword, count in (await db.execute(stmt)).all()
        ]

    async def trend(self, db: AsyncSession, *, days: int = 30) -> dict:
        days = max(1, min(int(days), MAX_DAYS))
        since = datetime.now() - timedelta(days=days - 1)

        stmt = (
            select(
                func.date(SearchHistory.created_at).label("day"),
                func.count().label("searches"),
                func.sum(
                    func.case((SearchHistory.results_count == 0, 1), else_=0)
                ).label("zero_result"),
            )
            .where(SearchHistory.created_at >= since)
            .group_by(func.date(SearchHistory.created_at))
        )
        rows = {
            str(day): (int(searches or 0), int(zero or 0))
            for day, searches, zero in (await db.execute(stmt)).all()
            if day is not None
        }

        points = []
        for offset in range(days):
            day = (since + timedelta(days=offset)).date().isoformat()
            searches, zero = rows.get(day, (0, 0))
            points.append({"day": day, "searches": searches, "zero_result": zero})
        return {"days": days, "points": points}


search_analytics_service = SearchAnalyticsService()
