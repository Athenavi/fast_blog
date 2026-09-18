"""monitor 模块路由（系统监控）

    GET    /api/v3/system/monitor/overview             总览聚合（服务器 + 在线）
    GET    /api/v3/system/monitor/server               服务器信息
    GET    /api/v3/system/monitor/online/stats         在线统计
    GET    /api/v3/system/monitor/online               在线会话列表（分页）
    DELETE /api/v3/system/monitor/online/{session_id}  强制下线

⚠️ ``/online/stats`` 是**静态路径**，必须注册在 ``/online/{session_id}`` 之前
（由 ``assert_no_shadowed_routes`` 在启动期强制）。

权限码：``module_system:monitor:view`` / ``:kick``；写操作经 ``OperationLogRoute`` 落审计日志。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
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
