"""export 模块路由（system 域：真表数据导出为 CSV / 预览）

::

    GET  /api/v3/system/export/templates        导出资源与字段清单
    GET  /api/v3/system/export/{resource}.csv   导出 CSV（**真实文件下载**）
    POST /api/v3/system/export/preview          前 N 行预览（JSON）

权限分两层：

  - **入口权限**：三个端点都要求 ``module_analytics:report:view``
    （"查看报表与导出"，是系统里语义最贴近"导出"的现成码）；
  - **资源细粒度权限**：导出 / 预览还会按该资源在 ``EXPORT_RESOURCES`` 登记的查看权限
    再校验一次（如导 ``users`` 需 ``module_system:user:view``）。superuser 与通配码放行，
    权限加载失败一律 fail-closed（403）。

CSV 端点返回**真实文件**（``Content-Disposition: attachment``，非统一响应包装）；
预览端点返回统一响应。Excel 导出未实现（未安装 openpyxl，不引入新依赖）。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Response

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.exceptions import ForbiddenError
from src.api.v3.core.permission import codes
from src.api.v3.core.permission.constants import WILDCARD_CODES
from src.api.v3.core.permission.loader import load_codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.export.schema import ExportPreviewRequest
from src.api.v3.modules.system.export.service import MAX_EXPORT_ROWS, export_service

router = APIRouter(prefix="/export", tags=["system-export"], route_class=OperationLogRoute)


async def _authorize_resource(db, user, resource: str) -> dict:
    """校验当前用户对该资源的细粒度导出权限

    未知资源 → 404（交给 ``export_service.spec``）；无权 → 403（fail-closed）。
    """
    spec = export_service.spec(resource)
    if getattr(user, "is_superuser", False):
        return spec
    try:
        owned = await load_codes(db, user.id)
    except Exception as exc:  # noqa: BLE001 - 权限加载失败必须拒绝，绝不放行
        raise ForbiddenError("权限校验失败") from exc
    required = spec["permission"]
    if WILDCARD_CODES & owned or required in owned:
        return spec
    raise ForbiddenError(f"导出 {resource} 需要权限 {required}")


@router.get("/templates", response_model=ResponseModel, summary="导出资源与字段清单")
async def export_templates(
    _current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
) -> dict:
    return resp.success(export_service.templates())


@router.post("/preview", response_model=ResponseModel, summary="导出预览（前 N 行 JSON）")
async def export_preview(
    payload: ExportPreviewRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
) -> dict:
    await _authorize_resource(db, current, payload.resource)
    return resp.success(
        await export_service.preview(
            db,
            payload.resource,
            limit=payload.limit,
            filters=payload.filters_dict(),
        )
    )


@router.get("/{resource}.csv", summary="导出 CSV（真实文件下载）")
async def export_csv(
    resource: str,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.REPORT_VIEW),
    limit: int = Query(default=MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
    keyword: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
) -> Response:
    await _authorize_resource(db, current, resource)
    payload, count = await export_service.export_csv(
        db,
        resource,
        limit=limit,
        filters={"keyword": keyword, "start": start, "end": end},
    )
    filename = f"{resource}-{datetime.now():%Y%m%d-%H%M%S}.csv"
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Rows": str(count),
        },
    )
