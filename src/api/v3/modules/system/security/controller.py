"""security 模块路由（T5-11 批次 3：自 astro `admin/security` 能力域新建）

::

    GET    /api/v3/system/security/overview              安全总览（24h 尝试/失败/锁定/黑名单）
    GET    /api/v3/system/security/attempts              登录尝试列表
    GET    /api/v3/system/security/blacklist             令牌黑名单列表
    DELETE /api/v3/system/security/blacklist/{entry_id}  删除黑名单记录
    GET    /api/v3/system/security/report/weekly         安全周报（近 7 天，真实聚合）
    GET    /api/v3/system/security/report/monthly        安全月报（近 30 天 + 安全评分）
    POST   /api/v3/system/security/report/archive        归档一份周期报表（写 report_history）
    GET    /api/v3/system/security/report/history        安全报表历史（读 report_history）

权限码：``module_system:security:view/delete``。
锁定账户管理已在 ``system/log``（lockouts / users history）覆盖，此处不重复。

周期报表自批次 8 起改为**真实数据库聚合**（``audit_logs`` + ``login_attempts``）：
``GET /report/{weekly,monthly}`` 只生成不落库（GET 不应有副作用），
``POST /report/archive`` 才写入 ``report_history``。v2 的内存态实现已弃用。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.security.report_service import security_report_service
from src.api.v3.modules.system.security.schema import SecurityReportArchiveRequest
from src.api.v3.modules.system.security.service import security_service

router = APIRouter(prefix="/security", tags=["system-security"], route_class=OperationLogRoute)


@router.get("/overview", response_model=ResponseModel, summary="安全总览")
async def overview(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
) -> dict:
    return resp.success(await security_service.overview(db))


@router.get("/attempts", response_model=ResponseModel, summary="登录尝试列表")
async def list_attempts(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    username: Optional[str] = Query(default=None),
    is_success: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await security_service.list_attempts(
        db, page=page, page_size=page_size, username=username, is_success=is_success
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/blacklist", response_model=ResponseModel, summary="令牌黑名单")
async def list_blacklist(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await security_service.list_blacklist(db, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)


@router.delete("/blacklist/{entry_id}", response_model=ResponseModel, summary="删除黑名单记录")
async def delete_blacklist(
    entry_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_DELETE),
) -> dict:
    await security_service.delete_blacklist(db, entry_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 周期报表（批次 8）
@router.get("/report/weekly", response_model=ResponseModel, summary="安全周报（近 7 天）")
async def security_weekly(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
) -> dict:
    """只生成不落库（GET 无副作用）；需要归档请调 ``POST /report/archive``。"""
    return resp.success(await security_report_service.build(db, kind="weekly"))


@router.get("/report/monthly", response_model=ResponseModel, summary="安全月报（近 30 天）")
async def security_monthly(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
) -> dict:
    return resp.success(await security_report_service.build(db, kind="monthly"))


@router.post("/report/archive", response_model=ResponseModel, summary="归档周期报表")
async def archive_security_report(
    payload: SecurityReportArchiveRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
) -> dict:
    return resp.success(
        await security_report_service.build(db, kind=payload.kind, store=True), msg="已归档"
    )


@router.get("/report/history", response_model=ResponseModel, summary="安全报表历史")
async def security_report_history(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SECURITY_VIEW),
    report_type: Optional[str] = Query(default=None, description="weekly / monthly"),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    return resp.success(
        await security_report_service.history(db, report_type=report_type, limit=limit)
    )
