"""approval 模块路由（T5-11 批次 2：自 astro `admin/approval` 能力域新建）

::

    GET    /api/v3/content/approval/record                  审批单列表
    GET    /api/v3/content/approval/record/{record_id}      审批单详情（含步骤）
    POST   /api/v3/content/approval/record                  提交审批单
    POST   /api/v3/content/approval/record/{record_id}/decision   通过 / 驳回
    DELETE /api/v3/content/approval/record/{record_id}      删除审批单

权限码：``module_content:approval:view/act/delete``。
内容发布与审批联动（文章提交审核时自动建单）属发布流程改造，随批次后续接入。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.approval.schema import ApprovalDecisionRequest, ApprovalRecordCreate
from src.api.v3.modules.content.approval.service import approval_service

router = APIRouter(prefix="/approval", tags=["content-approval"], route_class=OperationLogRoute)


@router.get("/record", response_model=ResponseModel, summary="审批单列表")
async def list_records(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.APPROVAL_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    content_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None, description="pending / approved / rejected"),
) -> dict:
    items, total = await approval_service.list_records(
        db, page=page, page_size=page_size, content_type=content_type, status=status
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/record", response_model=ResponseModel, summary="提交审批单")
async def create_record(
    payload: ApprovalRecordCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.APPROVAL_ACT),
) -> dict:
    return resp.success(
        await approval_service.create_record(db, payload, applicant_id=current.id), msg="已提交"
    )


@router.get("/record/{record_id}", response_model=ResponseModel, summary="审批单详情")
async def get_record(
    record_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.APPROVAL_VIEW),
) -> dict:
    return resp.success(await approval_service.get_record_with_steps(db, record_id))


@router.post("/record/{record_id}/decision", response_model=ResponseModel, summary="审批决定（通过/驳回）")
async def decide(
    record_id: int,
    payload: ApprovalDecisionRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.APPROVAL_ACT),
) -> dict:
    return resp.success(
        await approval_service.decide(db, record_id, payload, approver_id=current.id), msg="已处理"
    )


@router.delete("/record/{record_id}", response_model=ResponseModel, summary="删除审批单")
async def delete_record(
    record_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.APPROVAL_DELETE),
) -> dict:
    await approval_service.delete_record(db, record_id)
    return resp.success(None, msg="已删除")
