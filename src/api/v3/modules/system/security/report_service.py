"""security 模块的周期报表业务逻辑（T5-11 批次 8）

**数据源全部是数据库表** —— v2 的同名实现读的是**进程内内存结构**
（`anomaly_detector` / `security_alert_service` 的 list），多 worker 下各进程各自一份、
历史也只存在内存里，重启即丢。这里改为：

  - ``audit_logs``     ← 操作审计（总量 / 失败量 / 按级别 / 按状态 / TOP 动作）
  - ``login_attempts`` ← 登录尝试（总量 / 失败量 / TOP 失败 IP）

`security_score` 由**真实失败率**算出（操作失败率与登录失败率各占 40 分权重），
不是写死的常数。

报表生成后**真实写入** ``report_history`` 表（``report_type`` =
``security_weekly`` / ``security_monthly``，``scheduled_report_id`` 为空），
`/system/security/report/history` 从该表读取。
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.security.login_attempt import LoginAttempt
from shared.models.system.audit_log import AuditLog
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.analytics.report.crud import report_history_crud

WEEKLY_DAYS = 7
MONTHLY_DAYS = 30

#: 落库时的 report_type 取值（与 /report/history 的过滤保持一致）
WEEKLY_TYPE = "security_weekly"
MONTHLY_TYPE = "security_monthly"

#: 单次报表最多回看的天数（防止构造超大区间）
MAX_DAYS = 90


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


class SecurityReportService:
    """安全周期报表"""

    async def _count(self, db: AsyncSession, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await db.execute(stmt)).scalar() or 0)

    async def _group(
        self, db: AsyncSession, column, *conditions, limit: Optional[int] = None
    ) -> dict[str, int]:
        stmt = select(column, func.count()).where(*conditions).group_by(column)
        stmt = stmt.order_by(func.count().desc())
        if limit:
            stmt = stmt.limit(limit)
        return {
            str(key): int(count or 0)
            for key, count in (await db.execute(stmt)).all()
            if key is not None
        }

    async def _by_day(self, db: AsyncSession, column, since: datetime, *conditions) -> dict[str, int]:
        stmt = (
            select(func.date(column).label("day"), func.count())
            .where(column >= since, *conditions)
            .group_by(func.date(column))
        )
        return {
            str(day): int(count or 0)
            for day, count in (await db.execute(stmt)).all()
            if day is not None
        }

    async def build(self, db: AsyncSession, *, kind: str, store: bool = False) -> dict:
        """生成周报 / 月报（真实聚合）；``store=True`` 时同时写入 ``report_history``

        HTTP 层是分开的：``GET /report/{weekly,monthly}`` **只生成不落库**
        （GET 不应有副作用，避免被预取/重放灌入大量历史行），
        ``POST /report/archive`` 才落库。
        """
        if kind not in ("weekly", "monthly"):
            raise BadRequestError(f"安全报表周期不合法: {kind}（可选 weekly/monthly）")
        days = WEEKLY_DAYS if kind == "weekly" else MONTHLY_DAYS
        days = min(days, MAX_DAYS)
        now = datetime.now()
        since = now - timedelta(days=days - 1)

        audit_total = await self._count(db, AuditLog, AuditLog.created_at >= since)
        audit_failed = await self._count(
            db, AuditLog, AuditLog.created_at >= since, AuditLog.status == "failure"
        )
        login_total = await self._count(db, LoginAttempt, LoginAttempt.created_at >= since)
        login_failed = await self._count(
            db,
            LoginAttempt,
            LoginAttempt.created_at >= since,
            LoginAttempt.is_success.is_(False),
        )

        by_level = await self._group(db, AuditLog.level, AuditLog.created_at >= since)
        by_status = await self._group(db, AuditLog.status, AuditLog.created_at >= since)
        top_actions = await self._group(
            db, AuditLog.action, AuditLog.created_at >= since, limit=10
        )
        top_failed_ips = await self._group(
            db,
            LoginAttempt.ip_address,
            LoginAttempt.created_at >= since,
            LoginAttempt.is_success.is_(False),
            limit=10,
        )

        audit_by_day = await self._by_day(db, AuditLog.created_at, since)
        login_failed_by_day = await self._by_day(
            db, LoginAttempt.created_at, since, LoginAttempt.is_success.is_(False)
        )
        trend = []
        for offset in range(days):
            day = (since + timedelta(days=offset)).date().isoformat()
            trend.append(
                {
                    "day": day,
                    "audit_events": audit_by_day.get(day, 0),
                    "failed_logins": login_failed_by_day.get(day, 0),
                }
            )

        audit_failure_rate = round(audit_failed / audit_total * 100, 2) if audit_total else 0.0
        login_failure_rate = round(login_failed / login_total * 100, 2) if login_total else 0.0
        score = int(round(100 - audit_failure_rate * 0.4 - login_failure_rate * 0.4))
        score = max(0, min(100, score))

        report: dict[str, Any] = {
            "report_type": kind,
            "period": {"start": since, "end": now, "days": days},
            "summary": {
                "total_audit_events": audit_total,
                "failed_operations": audit_failed,
                "audit_failure_rate": audit_failure_rate,
                "total_login_attempts": login_total,
                "failed_logins": login_failed,
                "login_failure_rate": login_failure_rate,
            },
            "audit": {"by_level": by_level, "by_status": by_status, "top_actions": top_actions},
            "logins": {"top_failed_ips": top_failed_ips},
            "trend": trend,
            "generated_at": now,
        }
        if kind == "monthly":
            report["security_score"] = {"score": score, "grade": _grade(score), "level": score}

        if store:
            await report_history_crud.create(
                db,
                {
                    "scheduled_report_id": None,
                    "report_name": f"security-{kind}-{now:%Y%m%d}",
                    "report_type": WEEKLY_TYPE if kind == "weekly" else MONTHLY_TYPE,
                    "content": json.dumps(report, ensure_ascii=False, default=str),
                    "format": "json",
                    "generated_at": now,
                },
            )
        return report

    async def history(self, db: AsyncSession, *, report_type: Optional[str] = None, limit: int = 10):
        """从 ``report_history`` 表读安全报表历史（不返回 ``content`` 正文）"""
        types: Any = (WEEKLY_TYPE, MONTHLY_TYPE)
        if report_type:
            normalized = report_type if report_type.startswith("security_") else f"security_{report_type}"
            if normalized not in (WEEKLY_TYPE, MONTHLY_TYPE):
                raise BadRequestError(
                    f"报表类型不合法: {report_type}（可选 weekly/monthly）"
                )
            types = normalized
        rows, total = await report_history_crud.list(
            db,
            page=1,
            page_size=max(1, min(int(limit), 50)),
            filters={"report_type": types},
        )
        return {
            "reports": [
                {
                    "id": row.id,
                    "report_name": row.report_name,
                    "report_type": row.report_type,
                    "format": row.format,
                    "generated_at": row.generated_at,
                }
                for row in rows
            ],
            "count": total,
        }


security_report_service = SecurityReportService()
