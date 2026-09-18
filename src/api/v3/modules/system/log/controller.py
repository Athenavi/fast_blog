"""log 模块路由

::

    GET  /api/v3/system/log/audit                        审计日志分页
    GET  /api/v3/system/log/audit/export                 审计日志导出
    POST /api/v3/system/log/audit/cleanup                清理历史日志
    GET  /api/v3/system/log/lockouts                     当前被锁定的账号
    GET  /api/v3/system/log/users/{username}/history     某用户登录历史
    GET  /api/v3/system/log/users/{username}/stats       某用户登录安全统计

权限码：``settings:view`` / ``settings:edit``
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.log.schema import AuditCleanupRequest
from src.api.v3.modules.system.log.service import log_service

router = APIRouter(prefix="/log", tags=["system-log"], route_class=OperationLogRoute)


@router.get("/audit", response_model=ResponseModel, summary="审计日志")
async def list_audit_logs(
    page: PageDep,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.LOG_VIEW),
    user_id: Optional[int] = Query(default=None),
    action: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
) -> dict:
    logs, total = await log_service.list_audit_logs(
        db,
        page=page.page,
        page_size=page.page_size,
        keyword=page.keyword,
        user_id=user_id,
        action=action,
        level=level,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )
    return resp.success_page(logs, total, page.page, page.page_size)


@router.get("/audit/export", response_model=ResponseModel, summary="导出审计日志")
async def export_audit_logs(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.LOG_VIEW),
    output_format: str = Query(default="json", pattern="^(json|csv)$"),
    user_id: Optional[int] = Query(default=None),
    action: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
) -> dict:
    fmt, content = await log_service.export_audit_logs(
        db,
        output_format=output_format,
        user_id=user_id,
        action=action,
        level=level,
        start_date=start_date,
        end_date=end_date,
    )
    return resp.success({"format": fmt, "content": content, "count": content.count("\n")})


@router.post("/audit/cleanup", response_model=ResponseModel, summary="清理历史审计日志")
async def cleanup_audit_logs(
    payload: AuditCleanupRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.LOG_EDIT),
) -> dict:
    deleted = await log_service.cleanup_audit_logs(db, payload.days)
    return resp.success({"deleted": deleted}, msg=f"已清理 {deleted} 条")


@router.get("/lockouts", response_model=ResponseModel, summary="被锁定的账号")
async def locked_users(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.LOG_VIEW),
) -> dict:
    users = await log_service.locked_users(db)
    return resp.success_page(users, len(users), 1, len(users) or 1)


@router.get("/users/{username}/history", response_model=ResponseModel, summary="用户登录历史")
async def user_login_history(
    username: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.LOG_VIEW),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    history = await log_service.user_login_history(username, limit=limit, db=db)
    return resp.success({"username": username, "history": history, "count": len(history)})


@router.get("/users/{username}/stats", response_model=ResponseModel, summary="用户登录安全统计")
async def user_security_stats(
    username: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.LOG_VIEW),
) -> dict:
    stats = await log_service.user_security_stats(username, db=db)
    return resp.success({"username": username, "stats": stats})
