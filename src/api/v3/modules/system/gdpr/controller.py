"""gdpr 模块路由（T5-11 批次 3：自 astro `admin/gdpr` 能力域新建）

::

    GET    /api/v3/system/gdpr/consent             同意记录列表
    GET    /api/v3/system/gdpr/consent/stats       统计（按类型分组）
    DELETE /api/v3/system/gdpr/consent/{consent_id} 删除记录

权限码：``module_system:gdpr:view/delete``。
同意记录由前台授权动作写入；"用户数据导出/删除权"（数据可携带权）属于
跨模块流程，随后续批次接入。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.gdpr.service import gdpr_service

router = APIRouter(prefix="/gdpr", tags=["system-gdpr"], route_class=OperationLogRoute)


@router.get("/consent", response_model=ResponseModel, summary="同意记录列表")
async def list_consents(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GDPR_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: Optional[int] = Query(default=None),
    consent_type: Optional[str] = Query(default=None),
    granted: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await gdpr_service.list_consents(
        db, page=page, page_size=page_size, user_id=user_id,
        consent_type=consent_type, granted=granted,
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/consent/stats", response_model=ResponseModel, summary="同意统计")
async def consent_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GDPR_VIEW),
) -> dict:
    return resp.success(await gdpr_service.stats(db))


@router.delete("/consent/{consent_id}", response_model=ResponseModel, summary="删除记录")
async def delete_consent(
    consent_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.GDPR_DELETE),
) -> dict:
    await gdpr_service.delete_consent(db, consent_id)
    return resp.success(None, msg="已删除")
