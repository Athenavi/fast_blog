"""tipping 模块路由（commerce 域：打赏与提现）

::

    GET  /api/v3/commerce/tipping/config                          打赏配置（公开）
    GET  /api/v3/commerce/tipping/ranking                         打赏排行（公开）
    GET  /api/v3/commerce/tipping/article/{article_id}            某文章的打赏（公开）
    POST /api/v3/commerce/tipping/tip                             发起打赏（仅认证）
    POST /api/v3/commerce/tipping/callback/{provider}             网关回调（公开，插件验签）
    GET  /api/v3/commerce/tipping/mine                            我打赏出去的（仅认证）
    GET  /api/v3/commerce/tipping/received                        我收到的打赏（仅认证）
    GET  /api/v3/commerce/tipping/earnings                        我的收益概要（仅认证）
    POST /api/v3/commerce/tipping/withdraw                        申请提现（仅认证）
    GET  /api/v3/commerce/tipping/withdrawals/mine                我的提现记录（仅认证）
    GET  /api/v3/commerce/tipping/withdrawals                     提现列表
    POST /api/v3/commerce/tipping/withdrawals/{withdrawal_id}/review  审核提现
    POST /api/v3/commerce/tipping/withdrawals/{withdrawal_id}/paid    标记已打款
    GET  /api/v3/commerce/tipping/stats                           打赏统计

权限码：``module_commerce:tipping:{view,edit}``。

**打赏的钱走真实支付**：``POST /tip`` 会调批次 7 的 payment-gateway 插件下单，
只有网关回调经插件**验签通过**后才会把打赏置为 ``paid``（没验签就永远停在 pending）。
``POST /callback/{provider}`` 因此没有权限码（它是网关来调的），已登记写操作豁免。
"""

from typing import Optional

from fastapi import APIRouter, Query, Request

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.commerce.tipping.schema import (
    TipCreateRequest,
    WithdrawCreateRequest,
    WithdrawalPaidRequest,
    WithdrawalReviewRequest,
)
from src.api.v3.modules.commerce.tipping.service import tipping_service

router = APIRouter(prefix="/tipping", tags=["commerce-tipping"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 公开
@router.get("/config", response_model=ResponseModel, summary="打赏配置")
async def tip_config() -> dict:
    """金额范围 / 预设 / 提现门槛与费率（不查库）"""
    return resp.success(tipping_service.config())


@router.get("/ranking", response_model=ResponseModel, summary="打赏排行")
async def tip_ranking(
    db: DBSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """公开：按累计收到金额排序（只统计已支付的打赏）"""
    return resp.success(await tipping_service.ranking(db, limit=limit))


@router.get("/article/{article_id}", response_model=ResponseModel, summary="某文章的打赏")
async def article_tips(
    article_id: int,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """公开：只列出**已支付**的打赏（pending 的属于未完成的支付，不对外展示）"""
    items, total = await tipping_service.article_tips(
        db, article_id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/callback/{provider}", response_model=ResponseModel, summary="打赏网关回调")
async def tip_callback(provider: str, request: Request, db: DBSession) -> dict:
    """网关回调：**验签通过**才把打赏置为 paid（验签逻辑复用 PaymentFlowService）"""
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 - 表单回调也支持
        form = await request.form()
        payload = dict(form)
    headers = {key.lower(): value for key, value in request.headers.items()}
    return resp.success(
        await tipping_service.handle_callback(
            db, provider=provider, payload=payload, headers=headers
        )
    )


# ---------------------------------------------------------------- 我的
@router.post("/tip", response_model=ResponseModel, summary="发起打赏")
async def create_tip(
    payload: TipCreateRequest, db: DBSession, current: CurrentUser
) -> dict:
    """返回 ``{tip, payment}``：``payment`` 是支付插件的调起参数"""
    return resp.success(await tipping_service.create(db, current.id, payload), msg="已创建打赏订单")


@router.get("/mine", response_model=ResponseModel, summary="我打赏出去的")
async def my_tips(
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await tipping_service.my_tips(
        db, current.id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/received", response_model=ResponseModel, summary="我收到的打赏")
async def received_tips(
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await tipping_service.received(
        db, current.id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/earnings", response_model=ResponseModel, summary="我的收益概要")
async def my_earnings(db: DBSession, current: CurrentUser) -> dict:
    """分单位：`available` 才是可提现额（已结算 − 已占用）"""
    return resp.success(await tipping_service.earnings(db, current.id))


@router.post("/withdraw", response_model=ResponseModel, summary="申请提现")
async def apply_withdraw(
    payload: WithdrawCreateRequest, db: DBSession, current: CurrentUser
) -> dict:
    return resp.success(await tipping_service.withdraw(db, current.id, payload), msg="提现申请已提交")


@router.get("/withdrawals/mine", response_model=ResponseModel, summary="我的提现记录")
async def my_withdrawals(
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await tipping_service.my_withdrawals(
        db, current.id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


# ---------------------------------------------------------------- 管理端
@router.get("/withdrawals", response_model=ResponseModel, summary="提现列表")
async def list_withdrawals(
    db: DBSession,
    _current: CurrentUser,
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _perm=AuthControl(codes.TIPPING_VIEW),
) -> dict:
    items, total = await tipping_service.withdrawals(
        db, status=status, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/stats", response_model=ResponseModel, summary="打赏统计")
async def tip_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.TIPPING_VIEW),
) -> dict:
    return resp.success(await tipping_service.stats(db))


@router.post("/withdrawals/{withdrawal_id}/review", response_model=ResponseModel, summary="审核提现")
async def review_withdrawal(
    withdrawal_id: int,
    payload: WithdrawalReviewRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.TIPPING_EDIT),
) -> dict:
    return resp.success(
        await tipping_service.review_withdrawal(db, withdrawal_id, payload, current.id),
        msg="已批准" if payload.approve else "已驳回",
    )


@router.post("/withdrawals/{withdrawal_id}/paid", response_model=ResponseModel, summary="标记已打款")
async def mark_withdrawal_paid(
    withdrawal_id: int,
    payload: WithdrawalPaidRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.TIPPING_EDIT),
) -> dict:
    """人工转账完成后登记流水号（**不接受无凭据的"已完成"**）"""
    return resp.success(
        await tipping_service.mark_paid(db, withdrawal_id, payload, current.id), msg="已标记打款"
    )
