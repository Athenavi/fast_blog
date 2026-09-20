"""告警 / 指标 / SLA 三组业务逻辑（T5-11 批次 10）

**v2 没有 monitoring 模块** —— 只有散在 ``dashboard/realtime_monitor.py`` 与
``performance/performance_monitor.py`` 的**进程内内存**实现（重启即丢、多 worker 各一份），
且**完全没有 SLA 能力**。因此这三组是按表结构
（``monitoring_alerts`` / ``monitoring_metrics`` / ``sla_reports``）新建的**真实实现**：

  - **告警**：外部探针写入 → 列表 / 过滤 / 更新 / 解决 / 删除 / 统计（按类型、严重程度、未解决数）；
  - **指标**：时序写入 → 列表 / 按名称聚合出**时间桶**（PostgreSQL ``date_trunc``）/ 按保留期清理；
  - **SLA**：**真实计算** —— 由周期内 ``critical`` 告警的**合并时长**推导宕机分钟数，
    ``uptime = (总分钟 - 宕机) / 总分钟 × 100``，与目标比对得出 ``is_compliant``。

数据由外部探针 / 脚本写入（v3 只负责管理与查询），这一点与 v2 的"自己产生假数据"不同。
"""

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.monitoring import MonitoringAlert, MonitoringMetric, SLAReport
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.modules.system.monitor.crud import (
    monitoring_alert_crud,
    monitoring_metric_crud,
    sla_report_crud,
)
from src.api.v3.modules.system.monitor.schema import (
    ALERT_SEVERITIES,
    METRIC_BUCKETS,
    AlertCreate,
    AlertOut,
    AlertUpdate,
    MetricCreate,
    MetricOut,
    SLAComputeRequest,
    SLACreate,
    SLAOut,
    SLAUpdate,
)

MAX_PAGE_SIZE = 200


def _dump_json(value) -> Optional[str]:
    return json.dumps(value, ensure_ascii=False) if value else None


def _alert_out(row) -> dict:
    return AlertOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _metric_out(row) -> dict:
    return MetricOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _sla_out(row) -> dict:
    return SLAOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _merge_minutes(windows: list[tuple[datetime, datetime]]) -> int:
    """把若干时间窗口**合并**后统计总分钟数（重叠部分只算一次）"""
    if not windows:
        return 0
    ordered = sorted(windows, key=lambda item: item[0])
    total = timedelta()
    cur_start, cur_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            total += cur_end - cur_start
            cur_start, cur_end = start, end
    total += cur_end - cur_start
    return int(total.total_seconds() // 60)


class MonitoringAlertService:
    """监控告警"""

    async def list_alerts(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        source: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await monitoring_alert_crud.list(
            db,
            page=page,
            page_size=min(page_size, MAX_PAGE_SIZE),
            keyword=keyword,
            filters={
                "alert_type": alert_type,
                "severity": severity,
                "is_resolved": is_resolved,
                "source": source,
            },
        )
        return [_alert_out(row) for row in rows], total

    async def get_alert(self, db: AsyncSession, alert_id: int) -> dict:
        row = await monitoring_alert_crud.get(db, alert_id)
        if row is None:
            raise NotFoundError("告警不存在")
        return _alert_out(row)

    async def create_alert(self, db: AsyncSession, payload: AlertCreate) -> dict:
        if payload.severity not in ALERT_SEVERITIES:
            raise BadRequestError(
                f"严重程度不合法: {payload.severity}（可选 {'/'.join(ALERT_SEVERITIES)}）"
            )
        now = datetime.now()
        row = await monitoring_alert_crud.create(
            db,
            payload.model_dump(exclude={"notified_users"})
            | {
                "notified_users": _dump_json(payload.notified_users),
                "is_resolved": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        return _alert_out(row)

    async def update_alert(
        self, db: AsyncSession, alert_id: int, payload: AlertUpdate
    ) -> dict:
        row = await monitoring_alert_crud.get(db, alert_id)
        if row is None:
            raise NotFoundError("告警不存在")
        data = payload.model_dump(exclude_unset=True)
        if "severity" in data and data["severity"] not in ALERT_SEVERITIES:
            raise BadRequestError(f"严重程度不合法: {data['severity']}")
        if "notified_users" in data:
            data["notified_users"] = _dump_json(data.pop("notified_users"))
        if data.get("is_resolved") and row.resolved_at is None:
            data["resolved_at"] = datetime.now()
        updated = await monitoring_alert_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _alert_out(updated)

    async def resolve_alert(self, db: AsyncSession, alert_id: int) -> dict:
        row = await monitoring_alert_crud.get(db, alert_id)
        if row is None:
            raise NotFoundError("告警不存在")
        if row.is_resolved:
            raise BadRequestError("该告警已解决")
        now = datetime.now()
        updated = await monitoring_alert_crud.update(
            db, row, {"is_resolved": True, "resolved_at": now, "updated_at": now}
        )
        return _alert_out(updated)

    async def delete_alert(self, db: AsyncSession, alert_id: int) -> None:
        row = await monitoring_alert_crud.get(db, alert_id)
        if row is None:
            raise NotFoundError("告警不存在")
        await monitoring_alert_crud.remove(db, row)

    async def stats(self, db: AsyncSession) -> dict:
        """按类型 / 严重程度分组的真实聚合"""
        by_type = (
            await db.execute(
                select(MonitoringAlert.alert_type, func.count())
                .group_by(MonitoringAlert.alert_type)
                .order_by(func.count().desc())
            )
        ).all()
        by_severity = (
            await db.execute(
                select(MonitoringAlert.severity, func.count())
                .group_by(MonitoringAlert.severity)
                .order_by(func.count().desc())
            )
        ).all()
        total = int(
            (await db.execute(select(func.count()).select_from(MonitoringAlert))).scalar() or 0
        )
        unresolved = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(MonitoringAlert)
                    .where(MonitoringAlert.is_resolved.is_(False))
                )
            ).scalar()
            or 0
        )
        return {
            "total": total,
            "unresolved": unresolved,
            "resolved": total - unresolved,
            "by_type": [
                {"alert_type": key, "count": int(count or 0)}
                for key, count in by_type
                if key is not None
            ],
            "by_severity": [
                {"severity": key, "count": int(count or 0)}
                for key, count in by_severity
                if key is not None
            ],
        }


class MonitoringMetricService:
    """监控指标（时序）"""

    async def list_metrics(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 50,
        keyword: Optional[str] = None,
        metric_name: Optional[str] = None,
        metric_type: Optional[str] = None,
        site_id: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await monitoring_metric_crud.list(
            db,
            page=page,
            page_size=min(page_size, MAX_PAGE_SIZE),
            keyword=keyword,
            filters={
                "metric_name": metric_name,
                "metric_type": metric_type,
                "site_id": site_id,
            },
        )
        # 时间区间在应用层过滤：CRUDBase 的 filters 只支持等值 / in_
        if start is not None or end is not None:
            rows = [
                row
                for row in rows
                if (row.timestamp is not None)
                   and (start is None or row.timestamp >= start)
                   and (end is None or row.timestamp <= end)
            ]
        return [_metric_out(row) for row in rows], total

    async def create_metric(self, db: AsyncSession, payload: MetricCreate) -> dict:
        row = await monitoring_metric_crud.create(
            db,
            payload.model_dump(exclude={"labels", "timestamp"})
            | {
                "labels": _dump_json(payload.labels),
                "timestamp": payload.timestamp or datetime.now(),
            },
        )
        return _metric_out(row)

    async def delete_metric(self, db: AsyncSession, metric_id: int) -> None:
        row = await monitoring_metric_crud.get(db, metric_id)
        if row is None:
            raise NotFoundError("指标不存在")
        await monitoring_metric_crud.remove(db, row)

    async def series(
        self,
        db: AsyncSession,
        *,
        metric_name: str,
        bucket: str = "hour",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> dict:
        """按名称聚合出**时间桶**序列（PostgreSQL ``date_trunc``）"""
        if bucket not in METRIC_BUCKETS:
            raise BadRequestError(f"时间桶不合法: {bucket}（可选 {'/'.join(METRIC_BUCKETS)}）")
        trunc = func.date_trunc(bucket, MonitoringMetric.timestamp)
        stmt = select(
            trunc.label("bucket"),
            func.avg(MonitoringMetric.metric_value).label("avg"),
            func.min(MonitoringMetric.metric_value).label("min"),
            func.max(MonitoringMetric.metric_value).label("max"),
            func.count().label("count"),
        ).where(MonitoringMetric.metric_name == metric_name)
        if start is not None:
            stmt = stmt.where(MonitoringMetric.timestamp >= start)
        if end is not None:
            stmt = stmt.where(MonitoringMetric.timestamp <= end)
        rows = (await db.execute(stmt.group_by(trunc).order_by(trunc))).all()
        return {
            "metric_name": metric_name,
            "bucket": bucket,
            "points": [
                {
                    "bucket": row.bucket,
                    "avg": float(row.avg) if row.avg is not None else None,
                    "min": float(row.min) if row.min is not None else None,
                    "max": float(row.max) if row.max is not None else None,
                    "count": int(row.count or 0),
                }
                for row in rows
            ],
        }

    async def prune(self, db: AsyncSession, *, retention_days: int) -> int:
        """按保留期**真实删除**过期指标，返回删除条数"""
        if retention_days < 1:
            raise BadRequestError("保留天数必须 ≥ 1")
        cutoff = datetime.now() - timedelta(days=retention_days)
        result = await db.execute(
            delete(MonitoringMetric).where(MonitoringMetric.timestamp < cutoff)
        )
        await db.commit()
        return int(getattr(result, "rowcount", 0) or 0)


class SLAService:
    """SLA 报表（真实计算）"""

    async def list_reports(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        license_id: Optional[int] = None,
        is_compliant: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await sla_report_crud.list(
            db,
            page=page,
            page_size=min(page_size, MAX_PAGE_SIZE),
            filters={"license_id": license_id, "is_compliant": is_compliant},
        )
        return [_sla_out(row) for row in rows], total

    async def get_report(self, db: AsyncSession, report_id: int) -> dict:
        row = await sla_report_crud.get(db, report_id)
        if row is None:
            raise NotFoundError("SLA 报表不存在")
        return _sla_out(row)

    async def _downtime_minutes(
        self, db: AsyncSession, period_start: datetime, period_end: datetime
    ) -> int:
        """周期内的宕机时长 = 所有 ``critical`` 告警窗口**合并**后的分钟数

        窗口 = ``created_at``（早于周期则截到周期起点）→ ``resolved_at``（未解决或晚于周期则截到周期终点）。
        """
        alerts, _total = await monitoring_alert_crud.list(
            db,
            page=1,
            page_size=0,  # 0 = 不分页
            filters={"severity": "critical"},
        )
        windows: list[tuple[datetime, datetime]] = []
        for row in alerts:
            begun = row.created_at or row.updated_at
            if begun is None or begun > period_end:
                continue
            begun = max(begun, period_start)
            finished = row.resolved_at or period_end
            finished = min(finished, period_end)
            if finished > begun:
                windows.append((begun, finished))
        return _merge_minutes(windows)

    @staticmethod
    def _total_minutes(period_start: datetime, period_end: datetime) -> int:
        total_minutes = int((period_end - period_start).total_seconds() // 60)
        if total_minutes <= 0:
            raise BadRequestError("周期结束时间必须晚于开始时间")
        return total_minutes

    async def compute(self, db: AsyncSession, payload: SLAComputeRequest) -> dict:
        """按真实告警数据计算并**写入**一条 SLA 报表"""
        total_minutes = self._total_minutes(payload.period_start, payload.period_end)
        downtime = await self._downtime_minutes(db, payload.period_start, payload.period_end)
        uptime = round((total_minutes - downtime) / total_minutes * 100, 2)
        now = datetime.now()
        row = await sla_report_crud.create(
            db,
            {
                "license_id": payload.license_id,
                "period_start": payload.period_start,
                "period_end": payload.period_end,
                "uptime_percentage": uptime,
                "target_percentage": payload.target_percentage,
                "is_compliant": uptime >= payload.target_percentage,
                "downtime_minutes": downtime,
                "total_minutes": total_minutes,
                "created_at": now,
                "checked_at": now,
            },
        )
        return _sla_out(row)

    async def create_report(self, db: AsyncSession, payload: SLACreate) -> dict:
        """手工登记一条报表；``uptime_percentage`` 不传时用同一套真实算法算出来"""
        total_minutes = self._total_minutes(payload.period_start, payload.period_end)
        if payload.uptime_percentage is None or payload.downtime_minutes is None:
            downtime = await self._downtime_minutes(db, payload.period_start, payload.period_end)
        else:
            downtime = payload.downtime_minutes
        uptime = (
            payload.uptime_percentage
            if payload.uptime_percentage is not None
            else round((total_minutes - downtime) / total_minutes * 100, 2)
        )
        now = datetime.now()
        row = await sla_report_crud.create(
            db,
            {
                "license_id": payload.license_id,
                "period_start": payload.period_start,
                "period_end": payload.period_end,
                "uptime_percentage": uptime,
                "target_percentage": payload.target_percentage,
                "is_compliant": uptime >= payload.target_percentage,
                "downtime_minutes": downtime,
                "total_minutes": total_minutes,
                "created_at": now,
                "checked_at": now,
            },
        )
        return _sla_out(row)

    async def update_report(self, db: AsyncSession, report_id: int, payload: SLAUpdate) -> dict:
        row = await sla_report_crud.get(db, report_id)
        if row is None:
            raise NotFoundError("SLA 报表不存在")
        data = payload.model_dump(exclude_unset=True)
        period_start = data.get("period_start", row.period_start)
        period_end = data.get("period_end", row.period_end)
        if period_start and period_end:
            total_minutes = self._total_minutes(period_start, period_end)
            data.setdefault("total_minutes", total_minutes)
        uptime = data.get("uptime_percentage", row.uptime_percentage)
        target = data.get("target_percentage", row.target_percentage)
        if uptime is not None and target is not None:
            data["is_compliant"] = float(uptime) >= float(target)
        data["checked_at"] = datetime.now()
        updated = await sla_report_crud.update(db, row, data)
        return _sla_out(updated)

    async def delete_report(self, db: AsyncSession, report_id: int) -> None:
        row = await sla_report_crud.get(db, report_id)
        if row is None:
            raise NotFoundError("SLA 报表不存在")
        await sla_report_crud.remove(db, row)

    async def stats(self, db: AsyncSession) -> dict:
        """SLA 达标情况的真实聚合"""
        total = int(
            (await db.execute(select(func.count()).select_from(SLAReport))).scalar() or 0
        )
        compliant = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(SLAReport)
                    .where(SLAReport.is_compliant.is_(True))
                )
            ).scalar()
            or 0
        )
        avg_uptime = (
            await db.execute(select(func.avg(SLAReport.uptime_percentage)))
        ).scalar()
        return {
            "total_reports": total,
            "compliant": compliant,
            "breached": total - compliant,
            "compliance_rate": round(compliant / total * 100, 2) if total else 0.0,
            "avg_uptime_percentage": round(float(avg_uptime), 2) if avg_uptime is not None else None,
        }


monitoring_alert_service = MonitoringAlertService()
monitoring_metric_service = MonitoringMetricService()
sla_service = SLAService()
