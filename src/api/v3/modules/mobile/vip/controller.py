"""mobile/vip 模块路由（前台 VIP 自助：开通 / 订阅 / 内容访问）

::

    GET  /api/v3/mobile/vip/my-subscription          我的订阅（状态 + 历史 + 待支付订单）
    POST /api/v3/mobile/vip/create-payment           开通 / 续费下单（仅认证）
    POST /api/v3/mobile/vip/my-subscription/cancel   取消本人订阅（仅认证）
    GET  /api/v3/mobile/vip/check-access             内容访问判定（仅认证）
    GET  /api/v3/mobile/vip/premium-content          付费内容列表（仅认证）
    POST /api/v3/mobile/vip/callback/{provider}      支付网关回调（匿名，插件验签）

鉴权：除回调外全部**仅需认证**（只操作本人数据）；回调的安全性完全由支付插件的
``verify_callback`` 验签把守 —— 三个写操作都已登记进 ``audit.EXEMPT_WRITE_ENDPOINTS``。

金额单位是**元**（与 ``vip_plans.price`` 一致）；订阅状态 0=进行中 / 1=已过期 / 2=已取消。
套餐列表复用 ``marketing/vip`` 的公开端点（``/marketing/vip/public/plans``），本模块不重复。
"""

from typing import Optional

from fastapi import APIRouter, Query, Request

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.mobile.vip.schema import (
    CancelSubscriptionRequest,
    CreatePaymentRequest,
)
from src.api.v3.modules.mobile.vip.service import mobile_vip_service

router = APIRouter(prefix="/vip", tags=["mobile-vip"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 我的订阅
@router.get("/my-subscription", response_model=ResponseModel, summary="我的订阅")
async def my_subscription(db: DBSession, current: CurrentUser) -> dict:
    """状态（是否 VIP / 等级 / 到期与剩余天数）+ 订阅历史 + 待支付订单"""
    return resp.success(await mobile_vip_service.my_subscription(db, current.id))


@router.post("/create-payment", response_model=ResponseModel, summary="开通 / 续费下单")
async def create_payment(
    payload: CreatePaymentRequest, db: DBSession, current: CurrentUser
) -> dict:
    """返回 ``{order, payment}``：金额只按套餐价格取，``payment`` 是支付插件的调起参数"""
    return resp.success(
        await mobile_vip_service.create_payment(db, current.id, payload), msg="支付订单已创建"
    )


@router.post("/my-subscription/cancel", response_model=ResponseModel, summary="取消本人订阅")
async def cancel_my_subscription(
    payload: CancelSubscriptionRequest, db: DBSession, current: CurrentUser
) -> dict:
    return resp.success(
        await mobile_vip_service.cancel_my_subscription(db, current.id, payload), msg="已取消订阅"
    )


# ---------------------------------------------------------------- 内容访问
@router.get("/check-access", response_model=ResponseModel, summary="内容访问判定")
async def check_access(
    db: DBSession,
    current: CurrentUser,
    article_id: Optional[int] = Query(default=None, description="按文章自身的 VIP 设置判定"),
    required_level: int = Query(default=0, ge=0, le=9, description="直接指定所需等级"),
) -> dict:
    return resp.success(
        await mobile_vip_service.check_access(
            db, current.id, article_id=article_id, required_level=required_level
        )
    )


@router.get("/premium-content", response_model=ResponseModel, summary="付费内容列表")
async def premium_content(
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """每条带 ``accessible``：当前用户是否真读得到（正文走 ``mobile/article/{id}/content``）"""
    items, total = await mobile_vip_service.premium_content(
        db, current.id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


# ---------------------------------------------------------------- 网关回调
@router.post("/callback/{provider}", response_model=ResponseModel, summary="VIP 支付网关回调")
async def vip_callback(provider: str, request: Request, db: DBSession) -> dict:
    """网关回调：**验签通过**才把订单置 paid 并开通订阅（重复投递幂等）"""
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 - 表单回调也支持
        form = await request.form()
        payload = dict(form)
    headers = {key.lower(): value for key, value in request.headers.items()}
    return resp.success(
        await mobile_vip_service.handle_callback(
            db, provider=provider, payload=payload, headers=headers
        )
    )
