"""
企业管理管理员端点 - V2增强
提供许可证、工单、部署脚本、监控告警的管理CRUD功能
"""
from datetime import datetime
from typing import Optional
from functools import wraps

from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.enterprise import (
    DeploymentLog, DeploymentScript, EnterpriseLicense,
    SupportTicket, SupportTicketReply,
)
from shared.models.monitoring import MonitoringAlert, MonitoringMetric
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db

router = APIRouter(tags=["enterprise-admin"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            return fail(str(e))
    return wrapper


async def _check_admin(current_user) -> bool:
    """检查管理员权限"""
    from shared.services.security.rbac_service import rbac_service
    return await rbac_service.check_permission(None, current_user.id, 'settings:update')


# ==================== 许可证管理（管理员） ====================

@router.get("/licenses", summary="获取所有企业许可证列表")
@_catch
async def list_licenses(
    license_type: Optional[str] = Query(None, description="许可证类型过滤"),
    is_active: Optional[bool] = Query(None, description="激活状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取所有企业许可证列表"""
    stmt = select(EnterpriseLicense).order_by(desc(EnterpriseLicense.created_at))

    if license_type:
        stmt = stmt.where(EnterpriseLicense.license_type == license_type)
    if is_active is not None:
        stmt = stmt.where(EnterpriseLicense.is_active == is_active)

    # 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    licenses = result.scalars().all()

    return ok(data={
        'items': [lic.to_dict() for lic in licenses],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size
    })


@router.get("/licenses/{license_id}", summary="获取许可证详情")
@_catch
async def get_license_detail(
    license_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取许可证详情"""
    stmt = select(EnterpriseLicense).where(EnterpriseLicense.id == license_id)
    result = await db.execute(stmt)
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return fail("License not found")

    return ok(data=license_obj.to_dict())


@router.put("/licenses/{license_id}", summary="更新许可证")
@_catch
async def update_license(
    license_id: int,
    company_name: Optional[str] = Body(None),
    contact_email: Optional[str] = Body(None),
    max_sites: Optional[int] = Body(None),
    support_level: Optional[str] = Body(None),
    sla_enabled: Optional[bool] = Body(None),
    sla_uptime_guarantee: Optional[float] = Body(None),
    is_active: Optional[bool] = Body(None),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：更新许可证信息"""
    stmt = select(EnterpriseLicense).where(EnterpriseLicense.id == license_id)
    result = await db.execute(stmt)
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return fail("License not found")

    try:
        if company_name is not None:
            license_obj.company_name = company_name
        if contact_email is not None:
            license_obj.contact_email = contact_email
        if max_sites is not None:
            license_obj.max_sites = max_sites
        if support_level is not None:
            license_obj.support_level = support_level
        if sla_enabled is not None:
            license_obj.sla_enabled = sla_enabled
        if sla_uptime_guarantee is not None:
            license_obj.sla_uptime_guarantee = sla_uptime_guarantee
        if is_active is not None:
            license_obj.is_active = is_active

        license_obj.updated_at = datetime.now()
        await db.commit()
        await db.refresh(license_obj)
    except Exception:
        await db.rollback()
        raise

    return ok(
        data=license_obj.to_dict(),
        msg="License updated successfully"
    )


@router.delete("/licenses/{license_id}", summary="停用许可证")
@_catch
async def deactivate_license(
    license_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：停用许可证"""
    stmt = select(EnterpriseLicense).where(EnterpriseLicense.id == license_id)
    result = await db.execute(stmt)
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return fail("License not found")

    try:
        license_obj.is_active = False
        license_obj.updated_at = datetime.now()
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="License deactivated")


# ==================== 技术支持工单管理（管理员） ====================

@router.get("/tickets", summary="获取所有工单列表")
@_catch
async def list_all_tickets(
    status: Optional[str] = Query(None, description="状态过滤"),
    priority: Optional[str] = Query(None, description="优先级过滤"),
    category: Optional[str] = Query(None, description="分类过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取所有工单列表"""
    stmt = select(SupportTicket).order_by(desc(SupportTicket.created_at))

    if status:
        stmt = stmt.where(SupportTicket.status == status)
    if priority:
        stmt = stmt.where(SupportTicket.priority == priority)
    if category:
        stmt = stmt.where(SupportTicket.category == category)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    tickets = result.scalars().all()

    return ok(data={
        'items': [t.to_dict() for t in tickets],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size
    })


@router.get("/tickets/{ticket_id}", summary="获取工单详情（含回复）")
@_catch
async def get_ticket_detail(
    ticket_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取工单详情及所有回复"""
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await db.execute(stmt)
    ticket = result.scalar_one_or_none()

    if not ticket:
        return fail("Ticket not found")

    # 获取回复
    reply_stmt = (
        select(SupportTicketReply)
        .where(SupportTicketReply.ticket_id == ticket_id)
        .order_by(SupportTicketReply.created_at)
    )
    reply_result = await db.execute(reply_stmt)
    replies = reply_result.scalars().all()

    ticket_data = ticket.to_dict()
    ticket_data['replies'] = [r.to_dict() for r in replies]

    return ok(data=ticket_data)


@router.put("/tickets/{ticket_id}", summary="更新工单状态")
@_catch
async def update_ticket(
    ticket_id: int,
    status: Optional[str] = Body(None, description="工单状态"),
    priority: Optional[str] = Body(None, description="优先级"),
    assigned_to: Optional[int] = Body(None, description="分配给"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：更新工单状态、优先级或分配"""
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await db.execute(stmt)
    ticket = result.scalar_one_or_none()

    if not ticket:
        return fail("Ticket not found")

    try:
        if status is not None:
            ticket.status = status
            if status == 'resolved':
                ticket.resolved_at = datetime.now()
            elif status == 'closed':
                ticket.closed_at = datetime.now()
        if priority is not None:
            ticket.priority = priority
        if assigned_to is not None:
            ticket.assigned_to = assigned_to

        ticket.updated_at = datetime.now()
        await db.commit()
        await db.refresh(ticket)
    except Exception:
        await db.rollback()
        raise

    return ok(
        data=ticket.to_dict(),
        msg="Ticket updated successfully"
    )


# ==================== 部署脚本管理（管理员） ====================

@router.get("/scripts", summary="获取所有部署脚本列表")
@_catch
async def list_scripts(
    script_type: Optional[str] = Query(None, description="脚本类型过滤"),
    is_active: Optional[bool] = Query(None, description="激活状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取所有部署脚本列表"""
    stmt = select(DeploymentScript).order_by(desc(DeploymentScript.created_at))

    if script_type:
        stmt = stmt.where(DeploymentScript.script_type == script_type)
    if is_active is not None:
        stmt = stmt.where(DeploymentScript.is_active == is_active)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    scripts = result.scalars().all()

    return ok(data={
        'items': [s.to_dict() for s in scripts],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size
    })


@router.get("/scripts/{script_id}", summary="获取脚本详情")
@_catch
async def get_script_detail(
    script_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取部署脚本详情"""
    stmt = select(DeploymentScript).where(DeploymentScript.id == script_id)
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()

    if not script:
        return fail("Script not found")

    return ok(data=script.to_dict())


@router.put("/scripts/{script_id}", summary="更新部署脚本")
@_catch
async def update_script(
    script_id: int,
    name: Optional[str] = Body(None),
    content: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    version: Optional[str] = Body(None),
    is_active: Optional[bool] = Body(None),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：更新部署脚本"""
    stmt = select(DeploymentScript).where(DeploymentScript.id == script_id)
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()

    if not script:
        return fail("Script not found")

    try:
        if name is not None:
            script.name = name
        if content is not None:
            script.content = content
        if description is not None:
            script.description = description
        if version is not None:
            script.version = version
        if is_active is not None:
            script.is_active = is_active

        script.updated_at = datetime.now()
        await db.commit()
        await db.refresh(script)
    except Exception:
        await db.rollback()
        raise

    return ok(
        data=script.to_dict(),
        msg="Script updated successfully"
    )


@router.delete("/scripts/{script_id}", summary="删除部署脚本")
@_catch
async def delete_script(
    script_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：删除部署脚本"""
    stmt = select(DeploymentScript).where(DeploymentScript.id == script_id)
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()

    if not script:
        return fail("Script not found")

    try:
        await db.delete(script)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="Script deleted")


# ==================== 部署日志管理 ====================

@router.get("/logs", summary="获取部署日志列表")
@_catch
async def list_deployment_logs(
    script_id: Optional[int] = Query(None, description="脚本ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取部署日志列表"""
    stmt = select(DeploymentLog).order_by(desc(DeploymentLog.created_at))

    if script_id:
        stmt = stmt.where(DeploymentLog.script_id == script_id)
    if status:
        stmt = stmt.where(DeploymentLog.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return ok(data={
        'items': [log.to_dict() for log in logs],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size
    })


# ==================== 监控告警管理（管理员增强） ====================

@router.get("/alerts", summary="获取所有监控告警")
@_catch
async def list_alerts(
    severity: Optional[str] = Query(None, description="严重程度过滤"),
    alert_type: Optional[str] = Query(None, description="告警类型过滤"),
    is_resolved: Optional[bool] = Query(None, description="解决状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取所有监控告警（带分页）"""
    stmt = select(MonitoringAlert).order_by(desc(MonitoringAlert.created_at))

    if severity:
        stmt = stmt.where(MonitoringAlert.severity == severity)
    if alert_type:
        stmt = stmt.where(MonitoringAlert.alert_type == alert_type)
    if is_resolved is not None:
        stmt = stmt.where(MonitoringAlert.is_resolved == is_resolved)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return ok(data={
        'items': [a.to_dict() for a in alerts],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size
    })


@router.put("/alerts/{alert_id}/resolve", summary="标记告警为已解决")
@_catch
async def resolve_alert(
    alert_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：标记告警为已解决"""
    stmt = select(MonitoringAlert).where(MonitoringAlert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        return fail("Alert not found")

    try:
        alert.is_resolved = True
        alert.resolved_at = datetime.now()
        alert.updated_at = datetime.now()
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="Alert resolved")


@router.delete("/alerts/{alert_id}", summary="删除告警")
@_catch
async def delete_alert(
    alert_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：删除告警"""
    stmt = select(MonitoringAlert).where(MonitoringAlert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        return fail("Alert not found")

    try:
        await db.delete(alert)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="Alert deleted")


# ==================== 监控指标查询 ====================

@router.get("/metrics", summary="获取监控指标列表")
@_catch
async def list_metrics(
    metric_name: Optional[str] = Query(None, description="指标名称过滤"),
    metric_type: Optional[str] = Query(None, description="指标类型过滤"),
    hours: int = Query(24, description="最近N小时的数据"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取监控指标数据"""
    stmt = select(MonitoringMetric).order_by(desc(MonitoringMetric.timestamp))

    if metric_name:
        stmt = stmt.where(MonitoringMetric.metric_name == metric_name)
    if metric_type:
        stmt = stmt.where(MonitoringMetric.metric_type == metric_type)
    if hours > 0:
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=hours)
        stmt = stmt.where(MonitoringMetric.timestamp >= cutoff)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    metrics = result.scalars().all()

    return ok(data={
        'items': [m.to_dict() for m in metrics],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size
    })


# ==================== 企业管理概览统计 ====================

@router.get("/overview", summary="企业管理概览统计")
@_catch
async def get_enterprise_overview(
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """管理员：获取企业管理概览统计"""
    # 许可证统计
    license_total = (await db.execute(select(func.count(EnterpriseLicense.id)))).scalar() or 0
    license_active = (await db.execute(
        select(func.count(EnterpriseLicense.id)).where(EnterpriseLicense.is_active == True)
    )).scalar() or 0

    # 工单统计
    ticket_total = (await db.execute(select(func.count(SupportTicket.id)))).scalar() or 0
    ticket_open = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == 'open')
    )).scalar() or 0
    ticket_in_progress = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == 'in_progress')
    )).scalar() or 0

    # 部署脚本统计
    script_total = (await db.execute(select(func.count(DeploymentScript.id)))).scalar() or 0
    log_total = (await db.execute(select(func.count(DeploymentLog.id)))).scalar() or 0
    log_failed = (await db.execute(
        select(func.count(DeploymentLog.id)).where(DeploymentLog.status == 'failed')
    )).scalar() or 0

    # 监控告警统计
    alert_total = (await db.execute(select(func.count(MonitoringAlert.id)))).scalar() or 0
    alert_unresolved = (await db.execute(
        select(func.count(MonitoringAlert.id)).where(MonitoringAlert.is_resolved == False)
    )).scalar() or 0

    return ok(data={
        'licenses': {
            'total': license_total,
            'active': license_active,
        },
        'tickets': {
            'total': ticket_total,
            'open': ticket_open,
            'in_progress': ticket_in_progress,
        },
        'scripts': {
            'total': script_total,
            'deployments': log_total,
            'failed': log_failed,
        },
        'alerts': {
            'total': alert_total,
            'unresolved': alert_unresolved,
        }
    })
