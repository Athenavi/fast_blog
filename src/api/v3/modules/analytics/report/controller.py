"""report 模块路由（analytics 域：真实报表聚合 / 导出 / 定时报表 / 报表历史）

::

    GET    /api/v3/analytics/report/content                        内容报表
    GET    /api/v3/analytics/report/user-activity                  用户活跃报表
    GET    /api/v3/analytics/report/traffic                        流量报表
    POST   /api/v3/analytics/report/custom                         自定义报表
    POST   /api/v3/analytics/report/export                         导出（**真实文件下载**）
    GET    /api/v3/analytics/report/templates                      报表模板
    GET    /api/v3/analytics/report/scheduled                      定时报表列表
    POST   /api/v3/analytics/report/scheduled                      新建定时报表
    PUT    /api/v3/analytics/report/scheduled/{report_id}          更新定时报表
    DELETE /api/v3/analytics/report/scheduled/{report_id}          删除定时报表
    POST   /api/v3/analytics/report/scheduled/{report_id}/toggle   启停
    POST   /api/v3/analytics/report/scheduled/{report_id}/run      立即执行（写 report_history）
    GET    /api/v3/analytics/report/history                        报表历史列表
    GET    /api/v3/analytics/report/history/{history_id}/download  下载历史报表正文

权限码：``module_analytics:report:{view,create,edit,delete}``。

两个导出端点返回**真实文件**（``Content-Disposition: attachment``），不是统一响应包装。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Response

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.analytics.report.schema import (
    MAX_DAYS,
    MIN_DAYS,
    CustomReportRequest,
    ReportExportRequest,
    ScheduledReportCreate,
    ScheduledReportUpdate,
)
from src.api.v3.modules.analytics.report.service import REPORT_TEMPLATES, report_service

router = APIRouter(prefix="/report", tags=["analytics-report"], route_class=OperationLogRoute)

_DAYS_QUERY = Query(default=30, ge=MIN_DAYS, le=MAX_DAYS)


def _attachment(content: str, media_type: str, extension: str, prefix: str) -> Response:
    """构造带 ``Content-Disposition`` 的下载响应（CSV 加 BOM，Excel 才认 UTF-8 中文）"""
    payload = content.encode("utf-8-sig" if extension == "csv" else "utf-8")
    filename = f"{prefix}-{datetime.now():%Y%m%d-%H%M%S}.{extension}"
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------- 报表生成
@router.get("/content", response_model=ResponseModel, summary="内容报表")
async def content_report(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
    days: int = _DAYS_QUERY,
) -> dict:
    return resp.success(await report_service.content(db, days))


@router.get("/user-activity", response_model=ResponseModel, summary="用户活跃报表")
async def user_activity_report(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
    days: int = _DAYS_QUERY,
) -> dict:
    return resp.success(await report_service.user_activity(db, days))


@router.get("/traffic", response_model=ResponseModel, summary="流量报表")
async def traffic_report(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
    days: int = _DAYS_QUERY,
) -> dict:
    return resp.success(await report_service.traffic(db, days))


@router.post("/custom", response_model=ResponseModel, summary="自定义报表")
async def custom_report(
    payload: CustomReportRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
) -> dict:
    return resp.success(
        await report_service.custom(
            db, metrics=payload.metrics, days=payload.days, filters=payload.filters
        )
    )


@router.post("/export", summary="导出报表（JSON / CSV 文件下载）")
async def export_report(
    payload: ReportExportRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
) -> Response:
    report = await report_service.build(
        db,
        report_type=payload.report_type,
        days=payload.days,
        metrics=payload.metrics,
    )
    content, media_type, extension = report_service.render(report, payload.format)
    return _attachment(content, media_type, extension, f"report-{payload.report_type}")


@router.get("/templates", response_model=ResponseModel, summary="报表模板")
async def list_templates(
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
) -> dict:
    return resp.success({"templates": REPORT_TEMPLATES, "count": len(REPORT_TEMPLATES)})


# ---------------------------------------------------------------- 定时报表
@router.get("/scheduled", response_model=ResponseModel, summary="定时报表列表")
async def list_scheduled(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    report_type: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await report_service.list_scheduled(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        report_type=report_type,
        is_active=is_active,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/scheduled", response_model=ResponseModel, summary="新建定时报表")
async def create_scheduled(
    payload: ScheduledReportCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_CREATE),
) -> dict:
    return resp.success(await report_service.create_scheduled(db, payload), msg="已创建")


@router.put("/scheduled/{report_id}", response_model=ResponseModel, summary="更新定时报表")
async def update_scheduled(
    report_id: int,
    payload: ScheduledReportUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_EDIT),
) -> dict:
    return resp.success(await report_service.update_scheduled(db, report_id, payload), msg="已保存")


@router.delete("/scheduled/{report_id}", response_model=ResponseModel, summary="删除定时报表")
async def delete_scheduled(
    report_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_DELETE),
) -> dict:
    await report_service.delete_scheduled(db, report_id)
    return resp.success(None, msg="已删除")


@router.post("/scheduled/{report_id}/toggle", response_model=ResponseModel, summary="启停定时报表")
async def toggle_scheduled(
    report_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_EDIT),
) -> dict:
    return resp.success(await report_service.toggle_scheduled(db, report_id), msg="已更新")


@router.post("/scheduled/{report_id}/run", response_model=ResponseModel, summary="立即执行定时报表")
async def run_scheduled(
    report_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_EDIT),
) -> dict:
    return resp.success(await report_service.run_scheduled(db, report_id), msg="已执行并归档")


# ---------------------------------------------------------------- 报表历史
@router.get("/history", response_model=ResponseModel, summary="报表历史列表")
async def list_history(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    report_type: Optional[str] = Query(default=None),
    scheduled_report_id: Optional[int] = Query(default=None),
) -> dict:
    items, total = await report_service.list_history(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        report_type=report_type,
        scheduled_report_id=scheduled_report_id,
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/history/{history_id}/download", summary="下载报表历史正文")
async def download_history(
    history_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
) -> Response:
    row = await report_service.get_history_row(db, history_id)
    fmt = row.format or "json"
    extension = "csv" if fmt == "csv" else "json"
    media_type = "text/csv; charset=utf-8" if extension == "csv" else "application/json"
    return _attachment(row.content or "", media_type, extension, f"report-history-{row.id}")
