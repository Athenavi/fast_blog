"""audit 模块路由（审计日志导出）

::

    GET /api/v3/ops/audit/export?from=&to=&format=csv|json&limit=   导出审计日志（真实文件下载）

权限码：``module_ops:audit:export``。

产出的是**真实文件**（``Content-Disposition: attachment``）：CSV 带 UTF-8 BOM，
Excel 直接打开中文不乱码；JSON 便于程序处理。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import Response

from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.audit.service import audit_export_service

router = APIRouter(prefix="/audit", tags=["ops-audit"], route_class=OperationLogRoute)


@router.get("/export", summary="导出审计日志（真实文件下载）")
async def export_audit_logs(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AUDIT_EXPORT),
    date_from: Optional[datetime] = Query(default=None, alias="from", description="起始时间（含）"),
    date_to: Optional[datetime] = Query(default=None, alias="to", description="结束时间（含）"),
    fmt: str = Query(default="csv", alias="format", pattern="^(csv|json)$", description="导出格式"),
    limit: int = Query(default=5000, ge=1, le=50000, description="最多导出条数"),
) -> Response:
    """按时间区间导出写操作审计。缺省导出最近 5000 条。"""
    content, media_type, filename = await audit_export_service.export(
        db, date_from=date_from, date_to=date_to, fmt=fmt, limit=limit
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
