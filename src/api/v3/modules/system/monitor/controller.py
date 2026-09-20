"""monitor 模块路由（系统监控）

    GET    /api/v3/system/monitor/overview             总览聚合（服务器 + 在线）
    GET    /api/v3/system/monitor/server               服务器信息
    GET    /api/v3/system/monitor/online/stats         在线统计
    GET    /api/v3/system/monitor/online               在线会话列表（分页）
    DELETE /api/v3/system/monitor/online/{session_id}  强制下线
    # ── 批次 10：告警 / 指标 / SLA（数据由外部探针 / 脚本写入，v3 只负责管理与查询）──
    GET    /api/v3/system/monitor/alert                       告警列表
    POST   /api/v3/system/monitor/alert                       新建告警
    GET    /api/v3/system/monitor/alert/stats                 告警统计
    GET    /api/v3/system/monitor/alert/{alert_id}            告警详情
    PUT    /api/v3/system/monitor/alert/{alert_id}            更新告警
    POST   /api/v3/system/monitor/alert/{alert_id}/resolve    标记解决
    DELETE /api/v3/system/monitor/alert/{alert_id}            删除告警
    GET    /api/v3/system/monitor/metric                      指标列表
    POST   /api/v3/system/monitor/metric                      写入指标
    GET    /api/v3/system/monitor/metric/series               指标时间桶聚合
    DELETE /api/v3/system/monitor/metric/prune                按保留期清理
    DELETE /api/v3/system/monitor/metric/{metric_id}          删除指标
    GET    /api/v3/system/monitor/sla                         SLA 报表列表
    POST   /api/v3/system/monitor/sla                         登记 SLA 报表
    POST   /api/v3/system/monitor/sla/compute                 按真实告警计算并写入
    GET    /api/v3/system/monitor/sla/stats                   SLA 达标聚合
    GET    /api/v3/system/monitor/sla/{report_id}             SLA 详情
    PUT    /api/v3/system/monitor/sla/{report_id}             更新 SLA
    DELETE /api/v3/system/monitor/sla/{report_id}             删除 SLA

⚠️ 静态路径（``/online/stats``、``/alert/stats``、``/metric/series``、``/metric/prune``、
``/sla/compute``、``/sla/stats``）必须注册在各自的 ``/{id}`` 之前
（由 ``assert_no_shadowed_routes`` 在启动期强制）。

权限码：``module_system:monitor:view``（读）/ ``:kick`` / ``:manage``（告警 / 指标 / SLA 写操作）；
写操作经 ``OperationLogRoute`` 落审计日志。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.monitor.monitoring_service import (
    monitoring_alert_service,
    monitoring_metric_service,
    sla_service,
)
from src.api.v3.modules.system.monitor.schema import (
    AlertCreate,
    AlertUpdate,
    MetricCreate,
    SLAComputeRequest,
    SLACreate,
    SLAUpdate,
)
from src.api.v3.modules.system.monitor.service import monitor_service

router = APIRouter(prefix="/monitor", tags=["system-monitor"], route_class=OperationLogRoute)


@router.get("/overview", response_model=ResponseModel, summary="系统总览聚合")
async def monitor_overview(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
) -> dict:
    """服务器信息 + 在线统计一次返回，供总览页首屏使用"""
    return resp.success(
        data={
            "server": await monitor_service.server_info(),
            "online": await monitor_service.online_stats(db),
        }
    )


@router.get("/server", response_model=ResponseModel, summary="服务器信息")
async def monitor_server(
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
) -> dict:
    """CPU / 内存 / 磁盘 / 进程与运行时信息（psutil 采集）"""
    return resp.success(data=await monitor_service.server_info())


@router.get("/online/stats", response_model=ResponseModel, summary="在线统计")
async def online_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
) -> dict:
    """活跃会话数 / 窗口期内活跃数 / 去重用户数"""
    return resp.success(data=await monitor_service.online_stats(db))


@router.get("/online", response_model=ResponseModel, summary="在线会话列表")
async def online_list(
    db: DBSession,
    _current: CurrentUser,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    _perm=AuthControl(codes.MONITOR_VIEW),
) -> dict:
    """在线会话分页列表（**不返回 token**）"""
    items, total = await monitor_service.online_list(db, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)


@router.delete("/online/{session_id}", response_model=ResponseModel, summary="强制下线")
async def kick_online(
    session_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_KICK),
) -> dict:
    """把指定会话标记为下线（同时尽力清理 Redis 侧会话）"""
    if not await monitor_service.kick(db, session_id):
        return resp.fail("会话不存在", code=resp.CODE_NOT_FOUND)
    return resp.success(data={"session_id": session_id}, msg="已强制下线")


# ================================================================ 告警（批次 10）
@router.get("/alert", response_model=ResponseModel, summary="告警列表")
async def list_alerts(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: Optional[str] = Query(default=None),
    alert_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    is_resolved: Optional[bool] = Query(default=None),
    source: Optional[str] = Query(default=None),
) -> dict:
    items, total = await monitoring_alert_service.list_alerts(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        alert_type=alert_type,
        severity=severity,
        is_resolved=is_resolved,
        source=source,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/alert", response_model=ResponseModel, summary="新建告警")
async def create_alert(
    payload: AlertCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    return resp.success(await monitoring_alert_service.create_alert(db, payload), msg="已创建")


@router.get("/alert/stats", response_model=ResponseModel, summary="告警统计")
async def alert_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
) -> dict:
    return resp.success(await monitoring_alert_service.stats(db))


@router.get("/alert/{alert_id}", response_model=ResponseModel, summary="告警详情")
async def get_alert(
    alert_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
) -> dict:
    return resp.success(await monitoring_alert_service.get_alert(db, alert_id))


@router.put("/alert/{alert_id}", response_model=ResponseModel, summary="更新告警")
async def update_alert(
    alert_id: int,
    payload: AlertUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    return resp.success(
        await monitoring_alert_service.update_alert(db, alert_id, payload), msg="已保存"
    )


@router.post("/alert/{alert_id}/resolve", response_model=ResponseModel, summary="标记告警解决")
async def resolve_alert(
    alert_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    return resp.success(await monitoring_alert_service.resolve_alert(db, alert_id), msg="已解决")


@router.delete("/alert/{alert_id}", response_model=ResponseModel, summary="删除告警")
async def delete_alert(
    alert_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    await monitoring_alert_service.delete_alert(db, alert_id)
    return resp.success(None, msg="已删除")


# ================================================================ 指标（批次 10）
@router.get("/metric", response_model=ResponseModel, summary="指标列表")
async def list_metrics(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    keyword: Optional[str] = Query(default=None),
    metric_name: Optional[str] = Query(default=None),
    metric_type: Optional[str] = Query(default=None),
    site_id: Optional[int] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
) -> dict:
    items, total = await monitoring_metric_service.list_metrics(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        metric_name=metric_name,
        metric_type=metric_type,
        site_id=site_id,
        start=start,
        end=end,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/metric", response_model=ResponseModel, summary="写入指标")
async def create_metric(
    payload: MetricCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    return resp.success(await monitoring_metric_service.create_metric(db, payload), msg="已写入")


@router.get("/metric/series", response_model=ResponseModel, summary="指标时间桶聚合")
async def metric_series(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
    metric_name: str = Query(description="指标名称"),
    bucket: str = Query(default="hour", description="minute / hour / day"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
) -> dict:
    return resp.success(
        await monitoring_metric_service.series(
            db, metric_name=metric_name, bucket=bucket, start=start, end=end
        )
    )


@router.delete("/metric/prune", response_model=ResponseModel, summary="按保留期清理指标")
async def prune_metrics(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
    retention_days: int = Query(default=30, ge=1, le=3650),
) -> dict:
    deleted = await monitoring_metric_service.prune(db, retention_days=retention_days)
    return resp.success({"deleted": deleted}, msg="已清理")


@router.delete("/metric/{metric_id}", response_model=ResponseModel, summary="删除指标")
async def delete_metric(
    metric_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    await monitoring_metric_service.delete_metric(db, metric_id)
    return resp.success(None, msg="已删除")


# ================================================================ SLA（批次 10）
@router.get("/sla", response_model=ResponseModel, summary="SLA 报表列表")
async def list_sla_reports(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    license_id: Optional[int] = Query(default=None),
    is_compliant: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await sla_service.list_reports(
        db, page=page, page_size=page_size, license_id=license_id, is_compliant=is_compliant
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/sla", response_model=ResponseModel, summary="登记 SLA 报表")
async def create_sla_report(
    payload: SLACreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    """手工登记；``uptime_percentage`` 不传则用与 ``/sla/compute`` 相同的真实算法算出"""
    return resp.success(await sla_service.create_report(db, payload), msg="已登记")


@router.post("/sla/compute", response_model=ResponseModel, summary="按真实告警计算 SLA")
async def compute_sla(
    payload: SLAComputeRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    """宕机时长 = 周期内 ``critical`` 告警窗口**合并**后的分钟数；算出后写入一条报表"""
    return resp.success(await sla_service.compute(db, payload), msg="已计算并登记")


@router.get("/sla/stats", response_model=ResponseModel, summary="SLA 达标聚合")
async def sla_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
) -> dict:
    return resp.success(await sla_service.stats(db))


@router.get("/sla/{report_id}", response_model=ResponseModel, summary="SLA 详情")
async def get_sla_report(
    report_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
) -> dict:
    return resp.success(await sla_service.get_report(db, report_id))


@router.put("/sla/{report_id}", response_model=ResponseModel, summary="更新 SLA 报表")
async def update_sla_report(
    report_id: int,
    payload: SLAUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    return resp.success(await sla_service.update_report(db, report_id, payload), msg="已保存")


@router.delete("/sla/{report_id}", response_model=ResponseModel, summary="删除 SLA 报表")
async def delete_sla_report(
    report_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_MANAGE),
) -> dict:
    await sla_service.delete_report(db, report_id)
    return resp.success(None, msg="已删除")
