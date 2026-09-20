"""revenue 模块路由（commerce 域：收益记录 / 提现申请 / 分成配置 / 统计）

::

    GET    /api/v3/commerce/revenue/record                       收益记录列表
    POST   /api/v3/commerce/revenue/record                        新建收益记录（按分成配置计算）
    DELETE /api/v3/commerce/revenue/record/{record_id}            删除收益记录（对称回滚统计）
    GET    /api/v3/commerce/revenue/payout                        提现申请列表
    POST   /api/v3/commerce/revenue/payout/{payout_id}/approve    通过提现
    POST   /api/v3/commerce/revenue/payout/{payout_id}/complete   标记打款完成
    POST   /api/v3/commerce/revenue/payout/{payout_id}/reject     驳回提现（退还余额）
    GET    /api/v3/commerce/revenue/config                        分成配置列表
    PUT    /api/v3/commerce/revenue/config/{revenue_type}         更新分成配置
    GET    /api/v3/commerce/revenue/stats                         平台统计
    GET    /api/v3/commerce/revenue/stats/user/{user_id}          某用户的收益汇总

权限码：``module_commerce:revenue:{view,create,edit,delete}``。

**用户「我的收益」不在这里** —— 见 ``mobile/revenue``（仅认证、只操作本人）。
本模块全部是管理端能力，按 ``module_commerce:revenue:*`` 鉴权。

真实打款通道属二期：``complete`` 只做状态流转（``approved`` → ``completed``），不发起任何外部转账。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.commerce.revenue.schema import (
    PayoutDecision,
    RevenueRecordCreate,
    SharingConfigUpdate,
)
from src.api.v3.modules.commerce.revenue.service import (
    payout_service,
    revenue_record_service,
    sharing_config_service,
)

router = APIRouter(prefix="/revenue", tags=["commerce-revenue"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 收益记录
@router.get("/record", response_model=ResponseModel, summary="收益记录列表")
async def list_records(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    revenue_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    reference_type: Optional[str] = Query(default=None),
) -> dict:
    items, total = await revenue_record_service.list_records(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        user_id=user_id,
        revenue_type=revenue_type,
        status=status,
        reference_type=reference_type,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/record", response_model=ResponseModel, summary="新建收益记录")
async def create_record(
    payload: RevenueRecordCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_CREATE),
) -> dict:
    return resp.success(await revenue_record_service.create_record(db, payload), msg="已创建")


@router.delete("/record/{record_id}", response_model=ResponseModel, summary="删除收益记录")
async def delete_record(
    record_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_DELETE),
) -> dict:
    await revenue_record_service.delete_record(db, record_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 提现申请
@router.get("/payout", response_model=ResponseModel, summary="提现申请列表")
async def list_payouts(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
) -> dict:
    items, total = await payout_service.list_payouts(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        user_id=user_id,
        status=status,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/payout/{payout_id}/approve", response_model=ResponseModel, summary="通过提现申请")
async def approve_payout(
    payout_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_EDIT),
    payload: Optional[PayoutDecision] = None,
) -> dict:
    return resp.success(
        await payout_service.approve(
            db, payout_id, admin_id=current.id, notes=(payload.notes if payload else None)
        ),
        msg="已通过",
    )


@router.post("/payout/{payout_id}/complete", response_model=ResponseModel, summary="标记打款完成")
async def complete_payout(
    payout_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_EDIT),
    payload: Optional[PayoutDecision] = None,
) -> dict:
    return resp.success(
        await payout_service.complete(
            db, payout_id, admin_id=current.id, notes=(payload.notes if payload else None)
        ),
        msg="已完成打款",
    )


@router.post("/payout/{payout_id}/reject", response_model=ResponseModel, summary="驳回提现申请")
async def reject_payout(
    payout_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_EDIT),
    payload: Optional[PayoutDecision] = None,
) -> dict:
    return resp.success(
        await payout_service.reject(
            db, payout_id, admin_id=current.id, notes=(payload.notes if payload else None)
        ),
        msg="已驳回",
    )


# ---------------------------------------------------------------- 分成配置
@router.get("/config", response_model=ResponseModel, summary="分成配置列表")
async def list_configs(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_VIEW),
) -> dict:
    return resp.success(await sharing_config_service.list_configs(db))


@router.put("/config/{revenue_type}", response_model=ResponseModel, summary="更新分成配置")
async def update_config(
    revenue_type: str,
    payload: SharingConfigUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_EDIT),
) -> dict:
    return resp.success(
        await sharing_config_service.update_config(db, revenue_type, payload), msg="已保存"
    )


# ---------------------------------------------------------------- 统计
@router.get("/stats", response_model=ResponseModel, summary="平台收益统计")
async def platform_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_VIEW),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
) -> dict:
    return resp.success(
        await revenue_record_service.platform_stats(db, start_date=start_date, end_date=end_date)
    )


@router.get("/stats/user/{user_id}", response_model=ResponseModel, summary="某用户的收益汇总")
async def user_summary(
    user_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_VIEW),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
) -> dict:
    return resp.success(
        await revenue_record_service.user_summary(
            db, user_id, start_date=start_date, end_date=end_date
        )
    )
