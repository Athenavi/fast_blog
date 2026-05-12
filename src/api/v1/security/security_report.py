"""
安全报告 API

提供安全报告的生成和查看功能
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from shared.services.articles.anomaly_detector import anomaly_detector
from shared.services.security.security_alert import security_alert_service
from shared.services.security.security_report import report_generator
from src.api.v1.core.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.get("/daily", summary="生成日报", description="生成今日安全日报")
async def generate_daily_report(
        current_user=Depends(jwt_required),
):
    """生成日报"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 获取数据
    anomalies = anomaly_detector.get_anomalies(hours=24)
    alerts = security_alert_service.get_alert_history(hours=24)
    audit_logs = []  # TODO: 从审计日志服务获取

    report = report_generator.generate_daily_report(
        anomalies=anomalies,
        alerts=alerts,
        audit_logs=audit_logs,
    )

    return ApiResponse(
        success=True,
        data=report
    )


@router.get("/weekly", summary="生成周报", description="生成本周安全周报")
async def generate_weekly_report(
        current_user=Depends(jwt_required),
):
    """生成周报"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 获取数据
    anomalies = anomaly_detector.get_anomalies(hours=168)  # 7天
    alerts = security_alert_service.get_alert_history(hours=168)
    audit_logs = []  # TODO: 从审计日志服务获取

    report = report_generator.generate_weekly_report(
        anomalies=anomalies,
        alerts=alerts,
        audit_logs=audit_logs,
    )

    return ApiResponse(
        success=True,
        data=report
    )


@router.get("/monthly", summary="生成月报", description="生成本月安全月报")
async def generate_monthly_report(
        current_user=Depends(jwt_required),
):
    """生成月报"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 获取数据
    anomalies = anomaly_detector.get_anomalies(hours=720)  # 30天
    alerts = security_alert_service.get_alert_history(hours=720)
    audit_logs = []  # TODO: 从审计日志服务获取

    report = report_generator.generate_monthly_report(
        anomalies=anomalies,
        alerts=alerts,
        audit_logs=audit_logs,
    )

    return ApiResponse(
        success=True,
        data=report
    )


@router.get("/history", summary="获取报告历史", description="获取历史报告列表")
async def get_report_history(
        report_type: Optional[str] = Query(None, description="报告类型过滤 (daily, weekly, monthly)"),
        limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
        current_user=Depends(jwt_required),
):
    """获取报告历史"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    history = report_generator.get_report_history(
        report_type=report_type,
        limit=limit,
    )

    return ApiResponse(
        success=True,
        data={
            'reports': history,
            'count': len(history),
        }
    )


@router.get("/examples", summary="使用示例", description="获取安全报告使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "automated_reports": {
            'description': '自动化报告生成',
            'code_example': '''
from shared.services.security_report import report_generator
from shared.services.anomaly_detector import anomaly_detector
from shared.services.security_alert import security_alert_service
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 定时任务调度器
scheduler = AsyncIOScheduler()

# 每天凌晨生成日报
async def daily_report_job():
    anomalies = anomaly_detector.get_anomalies(hours=24)
    alerts = security_alert_service.get_alert_history(hours=24)
    
    report = report_generator.generate_daily_report(
        anomalies=anomalies,
        alerts=alerts,
        audit_logs=[]
    )
    
    # 发送邮件报告
    await send_report_email(report)

# 每周一生成周报
async def weekly_report_job():
    anomalies = anomaly_detector.get_anomalies(hours=168)
    alerts = security_alert_service.get_alert_history(hours=168)
    
    report = report_generator.generate_weekly_report(
        anomalies=anomalies,
        alerts=alerts,
        audit_logs=[]
    )
    
    await send_report_email(report)

# 配置调度
scheduler.add_job(daily_report_job, 'cron', hour=0, minute=0)
scheduler.add_job(weekly_report_job, 'cron', day_of_week='mon', hour=0, minute=0)
scheduler.start()
            '''.strip()
        },
        "report_structure": {
            'description': '报告结构说明',
            'daily_report': {
                'sections': [
                    '摘要：今日安全事件总数',
                    '异常事件：按类型和严重程度分类',
                    '告警统计：发送成功率和渠道分布',
                    'Top操作：最常见的管理操作',
                    '建议：针对性的改进建议',
                ]
            },
            'weekly_report': {
                'sections': [
                    '摘要：本周安全概况',
                    '趋势分析：每日事件变化',
                    '异常汇总：类型和严重程度分布',
                    '告警汇总：发送统计',
                    '对比分析：与上周对比',
                    '建议：本周改进建议',
                ]
            },
            'monthly_report': {
                'sections': [
                    '摘要：本月安全总结',
                    '趋势分析：每周事件变化',
                    '安全评分：综合安全评分和等级',
                    '异常汇总：详细统计分析',
                    '告警汇总：渠道效果评估',
                    '建议：长期改进策略',
                ]
            }
        },
        "integration_tips": {
            'description': '集成建议',
            'tips': [
                '将报告发送到管理层邮箱',
                '在仪表板展示安全评分',
                '设置阈值自动触发详细报告',
                '定期审查报告中的建议并执行',
                '保存历史报告用于趋势分析',
                '结合业务指标评估安全措施效果',
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
