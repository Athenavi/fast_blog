"""
SLA 监控服务模块
提供 SLA 达标率检查、报告生成和看板查询功能。
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_

from shared.models.monitoring.sla_report import SLAReport
from shared.models.enterprise_license import EnterpriseLicense
from src.unified_logger import default_logger as logger


class SLAService:
    """
    SLA 监控服务

    功能：
    1. 检查当前 SLA 达标率（基于监控指标计算在线率）
    2. 获取最近 N 天的 SLA 报告
    3. 获取所有活跃许可证的 SLA 看板
    """

    async def check_uptime(self, db: AsyncSession, license_id: int) -> SLAReport:
        """
        检查当前 SLA 达标率，并生成一份新的 SLA 报告。

        计算逻辑：
        - 查询企业许可证上的目标 SLA (sla_uptime_guarantee)
        - 基于最近的监控指标（如 uptime_check）统计在线率
        - 将结果记录到 sla_reports 表

        Args:
            db: 数据库会话
            license_id: 许可证 ID

        Returns:
            新生成的 SLA 报告对象
        """
        now = datetime.now()
        period_end = now
        period_start = now - timedelta(days=30)  # 默认以 30 天为周期

        # 获取许可证信息
        stmt = select(EnterpriseLicense).where(EnterpriseLicense.id == license_id)
        result = await db.execute(stmt)
        license_obj = result.scalar_one_or_none()

        if not license_obj:
            raise ValueError(f"Enterprise license not found: id={license_id}")

        target_pct = license_obj.sla_uptime_guarantee or 99.9

        # 从监控指标表统计在线率
        uptime_pct, downtime_min, total_min = await self._calculate_uptime(
            db, license_id, period_start, period_end
        )

        is_compliant = uptime_pct >= target_pct

        report = SLAReport(
            license_id=license_id,
            period_start=period_start,
            period_end=period_end,
            uptime_percentage=uptime_pct,
            target_percentage=target_pct,
            is_compliant=is_compliant,
            downtime_minutes=downtime_min,
            total_minutes=total_min,
            created_at=now,
            checked_at=now
        )

        db.add(report)
        await db.commit()
        await db.refresh(report)

        logger.info(
            f"SLA report generated: license_id={license_id}, "
            f"uptime={uptime_pct}%, target={target_pct}%, compliant={is_compliant}"
        )
        return report

    async def get_report(
            self,
            db: AsyncSession,
            license_id: int,
            days: int = 30
    ) -> List[SLAReport]:
        """
        获取最近 N 天的 SLA 报告

        Args:
            db: 数据库会话
            license_id: 许可证 ID
            days: 最近天数

        Returns:
            SLA 报告列表
        """
        cutoff = datetime.now() - timedelta(days=days)

        stmt = (
            select(SLAReport)
            .where(
                and_(
                    SLAReport.license_id == license_id,
                    SLAReport.checked_at >= cutoff
                )
            )
            .order_by(SLAReport.checked_at.desc())
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_dashboard(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        获取所有活跃许可证的 SLA 看板数据

        看板包含每个活跃许可证的最新 SLA 报告摘要。

        Args:
            db: 数据库会话

        Returns:
            看板数据列表
        """
        # 查询所有活跃且启用了 SLA 的许可证
        stmt = select(EnterpriseLicense).where(
            and_(
                EnterpriseLicense.is_active == True,
                EnterpriseLicense.sla_enabled == True
            )
        )
        result = await db.execute(stmt)
        licenses = result.scalars().all()

        dashboard = []

        for lic in licenses:
            # 获取该许可证最新的 SLA 报告
            report_stmt = (
                select(SLAReport)
                .where(SLAReport.license_id == lic.id)
                .order_by(SLAReport.checked_at.desc())
                .limit(1)
            )
            report_result = await db.execute(report_stmt)
            latest_report = report_result.scalar_one_or_none()

            dashboard.append({
                'license_id': lic.id,
                'company_name': lic.company_name,
                'license_type': lic.license_type,
                'target_percentage': lic.sla_uptime_guarantee,
                'latest_report': latest_report.to_dict() if latest_report else None,
            })

        return dashboard

    async def _calculate_uptime(
            self,
            db: AsyncSession,
            license_id: int,
            period_start: datetime,
            period_end: datetime
    ) -> tuple:
        """
        计算指定时间段内的在线率、宕机时间和总分钟数。

        基于 monitoring_metrics 表中名为 'uptime_check' 的指标进行统计。
        如果没有监控数据，默认返回 100% 在线率。

        Args:
            db: 数据库会话
            license_id: 许可证 ID
            period_start: 周期开始时间
            period_end: 周期结束时间

        Returns:
            (uptime_percentage, downtime_minutes, total_minutes) 元组
        """
        from shared.models.monitoring_metric import MonitoringMetric

        # 查询该时间段内的 uptime_check 指标
        stmt = (
            select(
                func.count(MonitoringMetric.id),
                func.sum(MonitoringMetric.metric_value)
            )
            .where(
                and_(
                    MonitoringMetric.metric_name == 'uptime_check',
                    MonitoringMetric.timestamp >= period_start,
                    MonitoringMetric.timestamp <= period_end,
                )
            )
        )

        result = await db.execute(stmt)
        row = result.one()

        total_checks = row[0] or 0
        total_value = row[1] or 0  # metric_value 累计值（假设1表示在线，0表示宕机）

        if total_checks == 0:
            # 无数据时默认 100%
            total_minutes = int((period_end - period_start).total_seconds() / 60)
            return 100.0, 0, max(total_minutes, 1)

        # 计算在线率
        uptime_pct = round(float(total_value) / float(total_checks) * 100, 2)
        total_minutes = int((period_end - period_start).total_seconds() / 60)
        downtime_min = int(total_minutes * (1 - float(total_value) / float(total_checks)))

        return uptime_pct, downtime_min, max(total_minutes, 1)


# 全局实例
sla_service = SLAService()
