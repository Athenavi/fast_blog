"""性能综合报告：把**已有真实数据源**聚合成一份体检报告

数据源（全部真实，不编造、不补零）：

  - **运行态 RUM**：``performance_tracker`` —— 前端 beacon 上报的真实 CWV
  - **数据库**：``slow_query_logger`` —— 引擎事件采集的真实慢查询
  - **服务器**：``psutil`` 实时采样（CPU / 内存 / 磁盘 / 进程）
  - **持久态**：``monitoring_alerts`` / ``monitoring_metrics`` / ``sla_reports`` 真表

两处**已知限制如实标注**（见响应的 ``notes``）：RUM 与慢查询统计是进程内队列
（多 worker 各一份、重启即丢）；服务器段落是采样瞬间值而非区间均值。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.monitoring.monitoring_metric import MonitoringMetric
from shared.services.performance.performance_tracker import performance_tracker
from shared.services.performance.slow_query_logger import slow_query_logger
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.monitor.monitoring_service import (
    monitoring_alert_service,
    sla_service,
)
from src.api.v3.modules.system.monitor.service import monitor_service

logger = get_logger("monitor.performance_report")


class PerformanceReportService:
    """性能综合报告（聚合真实数据源）"""

    async def report(self, db: AsyncSession, *, hours: int = 24, top: int = 5) -> Dict[str, Any]:
        since = datetime.now() - timedelta(hours=hours)

        metric_total = await db.scalar(
            select(func.count())
            .select_from(MonitoringMetric)
            .where(MonitoringMetric.timestamp >= since)
        )
        metric_rows = (
            await db.execute(
                select(
                    MonitoringMetric.metric_type,
                    func.count(),
                    func.avg(MonitoringMetric.metric_value),
                )
                .where(MonitoringMetric.timestamp >= since)
                .group_by(MonitoringMetric.metric_type)
            )
        ).all()

        by_type: List[Dict[str, Any]] = [
            {
                "metric_type": row[0] or "unknown",
                "count": int(row[1] or 0),
                "avg_value": float(row[2]) if row[2] is not None else None,
            }
            for row in metric_rows
        ]

        return {
            "period_hours": hours,
            "generated_at": datetime.now().isoformat(),
            # 运行态：前端 RUM（进程内队列）
            "runtime": {
                "overall": performance_tracker.get_overall_stats(hours=hours),
                "slowest_pages": performance_tracker.get_slowest_pages(hours=hours, limit=top),
            },
            # 数据库：真实采集的慢查询（进程内队列）
            "database": {
                "statistics": slow_query_logger.get_statistics(hours=hours),
                "threshold_ms": round(slow_query_logger.threshold * 1000, 2),
                "top_fingerprints": slow_query_logger.get_fingerprint_stats(hours=hours, limit=top),
                "n_plus_one": slow_query_logger.detect_n_plus_one(hours=hours),
            },
            # 服务器：采样瞬间值
            "server": await monitor_service.server_info(),
            # 持久态：数据库表
            "alerts": await monitoring_alert_service.stats(db),
            "metrics": {"total": int(metric_total or 0), "by_type": by_type},
            "sla": await sla_service.stats(db),
            "notes": [
                "runtime（RUM）与 database（慢查询）来自**进程内**队列：多 worker 部署下各进程一份，重启后清空",
                "server 段是采样瞬间值，不是区间均值",
                "alerts / metrics / sla 三段来自数据库表，为持久数据",
            ],
        }


performance_report_service = PerformanceReportService()
