"""maintenance 模块路由（任务 14c：维护模式）

::

    GET    /api/v3/system/maintenance/status        维护状态（公开）
    GET    /api/v3/system/maintenance/config        配置（需 setting:view）
    PUT    /api/v3/system/maintenance/config        保存配置（需 setting:edit）
    POST   /api/v3/system/maintenance/enable        开启（需 setting:edit）
    POST   /api/v3/system/maintenance/disable       关闭（需 setting:edit）
    PUT    /api/v3/system/maintenance/message       改提示语（需 setting:edit）
    POST   /api/v3/system/maintenance/schedule      设定时窗口（需 setting:edit）
    POST   /api/v3/system/maintenance/whitelist     加白名单 IP（需 setting:edit）
    DELETE /api/v3/system/maintenance/whitelist/{ip} 移除白名单 IP（需 setting:edit）

``status`` 公开是刻意的：前台需要它来展示维护页与倒计时。
写操作后会**主动失效中间件缓存**，让开关立即生效（不必等 5 秒 TTL）。
"""

from typing import Any, Dict

from fastapi import APIRouter, Body, Request

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.maintenance.schema import (
    MaintenanceEnableRequest,
    MaintenanceMessageRequest,
    MaintenanceScheduleRequest,
    MaintenanceWhitelistRequest,
)
from src.api.v3.modules.system.maintenance.service import maintenance_service

router = APIRouter(prefix="/maintenance", tags=["system-maintenance"], route_class=OperationLogRoute)


def _invalidate() -> None:
    from src.middleware.maintenance_mode import invalidate_cache

    invalidate_cache()


@router.get("/status", response_model=ResponseModel, summary="维护状态（公开）")
async def maintenance_status(db: DBSession, request: Request) -> dict:
    """``active`` = （人工开启 或 落在定时窗口内）且不在 IP 白名单"""
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )
    return resp.success(await maintenance_service.status(db, client_ip=client_ip))


@router.get("/config", response_model=ResponseModel, summary="维护模式配置")
async def get_maintenance_config(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(await maintenance_service.get_config(db))


@router.put("/config", response_model=ResponseModel, summary="保存维护模式配置")
async def save_maintenance_config(
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受已知配置项；未知键会被明确拒绝",
        examples=[{"enabled": True, "message": "升级中，10 分钟后回来"}],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    result = await maintenance_service.save_config(
        db, payload, user_id=getattr(current, "id", None)
    )
    _invalidate()
    return resp.success(result, msg="已保存")


@router.post("/enable", response_model=ResponseModel, summary="开启维护模式")
async def enable_maintenance(
    payload: MaintenanceEnableRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    result = await maintenance_service.enable(
        db,
        message=payload.message,
        whitelist_ips=payload.whitelist_ips,
        retry_after=payload.retry_after,
        user_id=getattr(current, "id", None),
    )
    _invalidate()
    return resp.success(result, msg="维护模式已开启")


@router.post("/disable", response_model=ResponseModel, summary="关闭维护模式")
async def disable_maintenance(
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    result = await maintenance_service.disable(db, user_id=getattr(current, "id", None))
    _invalidate()
    return resp.success(result, msg="维护模式已关闭")


@router.put("/message", response_model=ResponseModel, summary="修改维护提示语")
async def update_maintenance_message(
    payload: MaintenanceMessageRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    result = await maintenance_service.update_message(
        db, payload.message, user_id=getattr(current, "id", None)
    )
    _invalidate()
    return resp.success(result, msg="已更新")


@router.post("/schedule", response_model=ResponseModel, summary="设定时维护窗口")
async def schedule_maintenance(
    payload: MaintenanceScheduleRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    result = await maintenance_service.schedule(
        db,
        start=payload.scheduled_start,
        end=payload.scheduled_end,
        message=payload.message,
        user_id=getattr(current, "id", None),
    )
    _invalidate()
    return resp.success(result, msg="定时维护已设置")


@router.post("/whitelist", response_model=ResponseModel, summary="加入 IP 白名单")
async def add_whitelist_ip(
    payload: MaintenanceWhitelistRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    result = await maintenance_service.add_whitelist_ip(
        db, payload.ip, user_id=getattr(current, "id", None)
    )
    _invalidate()
    return resp.success(result, msg="已加入白名单")


@router.delete("/whitelist/{ip}", response_model=ResponseModel, summary="移出 IP 白名单")
async def remove_whitelist_ip(
    ip: str,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    result = await maintenance_service.remove_whitelist_ip(
        db, ip, user_id=getattr(current, "id", None)
    )
    _invalidate()
    return resp.success(result, msg="已移出白名单")
