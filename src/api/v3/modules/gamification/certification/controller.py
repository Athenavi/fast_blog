"""certification 模块路由（gamification 域：专家认证）

::

    GET  /api/v3/gamification/certification/types                 认证类型（公开）
    GET  /api/v3/gamification/certification/experts               认证专家列表（公开，自动排除过期）
    GET  /api/v3/gamification/certification/experts/{user_id}     某专家详情（公开）
    GET  /api/v3/gamification/certification/mine                  我的认证（仅认证）
    POST /api/v3/gamification/certification/apply                 提交申请（仅认证）
    PUT  /api/v3/gamification/certification/mine                  修改待审申请（仅认证）
    POST /api/v3/gamification/certification/mine/withdraw         撤回申请（仅认证）
    GET  /api/v3/gamification/certification/pending               待审队列
    POST /api/v3/gamification/certification/{cert_id}/review      审核（通过 / 驳回）
    POST /api/v3/gamification/certification/{cert_id}/revoke      撤销已通过的认证
    GET  /api/v3/gamification/certification/stats                 统计

权限码：``module_gamification:certification:{view,review}``。

静态段路由全部注册在 ``/{cert_id}/...`` 之前（启动期 ``assert_no_shadowed_routes`` 强制）。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.gamification.certification.schema import (
    CertificationActionRequest,
    CertificationApplyRequest,
    CertificationReviewRequest,
    CertificationUpdateRequest,
)
from src.api.v3.modules.gamification.certification.service import certification_service

router = APIRouter(
    prefix="/certification",
    tags=["gamification-certification"],
    route_class=OperationLogRoute,
)


# ---------------------------------------------------------------- 公开
@router.get("/types", response_model=ResponseModel, summary="认证类型")
async def cert_types() -> dict:
    return resp.success(certification_service.types())


@router.get("/experts", response_model=ResponseModel, summary="认证专家列表")
async def list_experts(
    db: DBSession,
    cert_type: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """公开：已通过且**未过期**的认证专家"""
    items, total = await certification_service.experts(
        db, cert_type=cert_type, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/experts/{user_id}", response_model=ResponseModel, summary="某专家详情")
async def expert_detail(user_id: int, db: DBSession) -> dict:
    return resp.success(await certification_service.expert_detail(db, user_id))


# ---------------------------------------------------------------- 我的认证
@router.get("/mine", response_model=ResponseModel, summary="我的认证")
async def my_certification(db: DBSession, current: CurrentUser) -> dict:
    """没有申请过时返回 `data = null`（不是 404）"""
    return resp.success(await certification_service.mine(db, current.id))


@router.post("/apply", response_model=ResponseModel, summary="提交认证申请")
async def apply_certification(
    payload: CertificationApplyRequest, db: DBSession, current: CurrentUser
) -> dict:
    return resp.success(
        await certification_service.apply(db, current.id, payload), msg="申请已提交，等待审核"
    )


@router.put("/mine", response_model=ResponseModel, summary="修改待审申请")
async def update_my_certification(
    payload: CertificationUpdateRequest, db: DBSession, current: CurrentUser
) -> dict:
    return resp.success(
        await certification_service.update_mine(db, current.id, payload), msg="已保存"
    )


@router.post("/mine/withdraw", response_model=ResponseModel, summary="撤回认证申请")
async def withdraw_certification(
    payload: CertificationActionRequest, db: DBSession, current: CurrentUser
) -> dict:
    return resp.success(
        await certification_service.withdraw(db, current.id, payload), msg="已撤回"
    )


# ---------------------------------------------------------------- 管理端
@router.get("/pending", response_model=ResponseModel, summary="待审认证队列")
async def pending_certifications(
    db: DBSession,
    _current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _perm=AuthControl(codes.CERTIFICATION_VIEW),
) -> dict:
    items, total = await certification_service.pending(db, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)


@router.get("/stats", response_model=ResponseModel, summary="认证统计")
async def certification_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CERTIFICATION_VIEW),
) -> dict:
    return resp.success(await certification_service.stats(db))


# 注意：以下两条是「3 段 + 动态段」路由，必须放在上面的静态 2 段路由之后
@router.post("/{cert_id}/review", response_model=ResponseModel, summary="审核认证")
async def review_certification(
    cert_id: int,
    payload: CertificationReviewRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.CERTIFICATION_REVIEW),
) -> dict:
    result = await certification_service.review(db, cert_id, payload, current.id)
    return resp.success(result, msg="已通过" if payload.approve else "已驳回")


@router.post("/{cert_id}/revoke", response_model=ResponseModel, summary="撤销认证")
async def revoke_certification(
    cert_id: int,
    payload: CertificationActionRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.CERTIFICATION_REVIEW),
) -> dict:
    return resp.success(
        await certification_service.revoke(db, cert_id, payload, current.id), msg="已撤销"
    )
