"""payment 模块路由（commerce 域：支付网关 / 交易 / 加密货币 / 税务 + 发起支付与回调）

::

    GET    /api/v3/commerce/payment/gateway                         网关列表
    POST   /api/v3/commerce/payment/gateway                         新建网关
    GET    /api/v3/commerce/payment/gateway/{gateway_id}            网关详情
    PUT    /api/v3/commerce/payment/gateway/{gateway_id}            更新网关
    DELETE /api/v3/commerce/payment/gateway/{gateway_id}            删除网关
    GET    /api/v3/commerce/payment/transaction                     交易列表
    POST   /api/v3/commerce/payment/transaction                     新建交易
    GET    /api/v3/commerce/payment/transaction/{transaction_id}    交易详情
    PUT    /api/v3/commerce/payment/transaction/{transaction_id}    更新交易
    DELETE /api/v3/commerce/payment/transaction/{transaction_id}    删除交易
    GET    /api/v3/commerce/payment/crypto                          加密支付列表
    POST   /api/v3/commerce/payment/crypto                          新建加密支付
    PUT    /api/v3/commerce/payment/crypto/{crypto_id}              更新加密支付
    DELETE /api/v3/commerce/payment/crypto/{crypto_id}              删除加密支付
    GET    /api/v3/commerce/payment/tax-config                      税务配置列表
    POST   /api/v3/commerce/payment/tax-config                      新建税务配置
    PUT    /api/v3/commerce/payment/tax-config/{config_id}          更新税务配置
    DELETE /api/v3/commerce/payment/tax-config/{config_id}          删除税务配置
    POST   /api/v3/commerce/payment/initiate                        发起支付（委托支付插件）
    POST   /api/v3/commerce/payment/callback/{provider}             网关回调（匿名）

权限码：``module_commerce:payment:{view,create,edit,delete}``。

**两个端点是刻意的例外**（均登记进 `core/permission/audit.py` 的豁免清单）：

  - ``POST /initiate``：**仅需登录**（前台用户给自己下单），不要求权限码；
  - ``POST /callback/{provider}``：**匿名**，网关服务端直连。安全性完全由支付插件的
    ``verify_callback`` 验签把守 —— 验签不通过一律不更新交易，且插件缺失时直接拒绝
    （见 ``service.PaymentFlowService``），**没有任何"本地降级放行"分支**。
"""

from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.commerce.payment.schema import (
    CryptoPaymentCreate,
    CryptoPaymentUpdate,
    PaymentGatewayCreate,
    PaymentGatewayUpdate,
    PaymentInitiateRequest,
    PaymentTransactionCreate,
    PaymentTransactionUpdate,
    TaxConfigCreate,
    TaxConfigUpdate,
)
from src.api.v3.modules.commerce.payment.service import (
    crypto_payment_service,
    payment_flow_service,
    payment_gateway_service,
    payment_transaction_service,
    tax_config_service,
)

router = APIRouter(prefix="/payment", tags=["commerce-payment"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 支付网关
@router.get("/gateway", response_model=ResponseModel, summary="支付网关列表")
async def list_gateways(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await payment_gateway_service.list_gateways(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        provider=provider,
        is_active=is_active,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/gateway", response_model=ResponseModel, summary="新建支付网关")
async def create_gateway(
    payload: PaymentGatewayCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_CREATE),
) -> dict:
    return resp.success(await payment_gateway_service.create_gateway(db, payload), msg="已创建")


@router.get("/gateway/{gateway_id}", response_model=ResponseModel, summary="支付网关详情")
async def get_gateway(
    gateway_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
) -> dict:
    return resp.success(await payment_gateway_service.get_gateway(db, gateway_id))


@router.put("/gateway/{gateway_id}", response_model=ResponseModel, summary="更新支付网关")
async def update_gateway(
    gateway_id: int,
    payload: PaymentGatewayUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(
        await payment_gateway_service.update_gateway(db, gateway_id, payload), msg="已保存"
    )


@router.delete("/gateway/{gateway_id}", response_model=ResponseModel, summary="删除支付网关")
async def delete_gateway(
    gateway_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_DELETE),
) -> dict:
    await payment_gateway_service.delete_gateway(db, gateway_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 支付交易
@router.get("/transaction", response_model=ResponseModel, summary="交易列表")
async def list_transactions(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None, description="订单号 / 第三方交易号"),
    status: Optional[str] = Query(default=None),
    payment_method: Optional[str] = Query(default=None),
    currency: Optional[str] = Query(default=None),
    user: Optional[int] = Query(default=None),
    gateway: Optional[int] = Query(default=None),
) -> dict:
    items, total = await payment_transaction_service.list_transactions(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status,
        payment_method=payment_method,
        currency=currency,
        user=user,
        gateway=gateway,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/transaction", response_model=ResponseModel, summary="新建交易")
async def create_transaction(
    payload: PaymentTransactionCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_CREATE),
) -> dict:
    return resp.success(
        await payment_transaction_service.create_transaction(db, payload), msg="已创建"
    )


@router.get("/transaction/{transaction_id}", response_model=ResponseModel, summary="交易详情")
async def get_transaction(
    transaction_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
) -> dict:
    return resp.success(await payment_transaction_service.get_transaction(db, transaction_id))


@router.put("/transaction/{transaction_id}", response_model=ResponseModel, summary="更新交易")
async def update_transaction(
    transaction_id: int,
    payload: PaymentTransactionUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(
        await payment_transaction_service.update_transaction(db, transaction_id, payload),
        msg="已保存",
    )


@router.delete("/transaction/{transaction_id}", response_model=ResponseModel, summary="删除交易")
async def delete_transaction(
    transaction_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_DELETE),
) -> dict:
    await payment_transaction_service.delete_transaction(db, transaction_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 加密货币支付
@router.get("/crypto", response_model=ResponseModel, summary="加密支付列表")
async def list_crypto(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None, description="钱包地址 / 交易哈希 / 代币"),
    blockchain: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    transaction: Optional[int] = Query(default=None),
) -> dict:
    items, total = await crypto_payment_service.list_crypto(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        blockchain=blockchain,
        status=status,
        transaction=transaction,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/crypto", response_model=ResponseModel, summary="新建加密支付")
async def create_crypto(
    payload: CryptoPaymentCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_CREATE),
) -> dict:
    return resp.success(await crypto_payment_service.create_crypto(db, payload), msg="已创建")


@router.put("/crypto/{crypto_id}", response_model=ResponseModel, summary="更新加密支付")
async def update_crypto(
    crypto_id: int,
    payload: CryptoPaymentUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(
        await crypto_payment_service.update_crypto(db, crypto_id, payload), msg="已保存"
    )


@router.delete("/crypto/{crypto_id}", response_model=ResponseModel, summary="删除加密支付")
async def delete_crypto(
    crypto_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_DELETE),
) -> dict:
    await crypto_payment_service.delete_crypto(db, crypto_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 税务配置
@router.get("/tax-config", response_model=ResponseModel, summary="税务配置列表")
async def list_tax_configs(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    tax_type: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await tax_config_service.list_tax_configs(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        country=country,
        region=region,
        tax_type=tax_type,
        is_active=is_active,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/tax-config", response_model=ResponseModel, summary="新建税务配置")
async def create_tax_config(
    payload: TaxConfigCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_CREATE),
) -> dict:
    return resp.success(await tax_config_service.create_tax_config(db, payload), msg="已创建")


@router.put("/tax-config/{config_id}", response_model=ResponseModel, summary="更新税务配置")
async def update_tax_config(
    config_id: int,
    payload: TaxConfigUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(
        await tax_config_service.update_tax_config(db, config_id, payload), msg="已保存"
    )


@router.delete("/tax-config/{config_id}", response_model=ResponseModel, summary="删除税务配置")
async def delete_tax_config(
    config_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_DELETE),
) -> dict:
    await tax_config_service.delete_tax_config(db, config_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 发起支付 / 回调
@router.post("/initiate", response_model=ResponseModel, summary="发起支付（委托支付插件）")
async def initiate_payment(
    payload: PaymentInitiateRequest,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    """仅需登录（已登记写操作豁免）：金额单位为**元**，转发插件时转成**分**。"""
    return resp.success(
        await payment_flow_service.initiate(db, payload, user_id=current.id), msg="已提交"
    )


@router.post("/callback/{provider}", summary="支付网关回调（匿名，插件验签）")
async def payment_callback(provider: str, request: Request, db: DBSession) -> Response:
    """网关服务端直连，**无鉴权**（已登记写操作豁免）。

    请求体可能是 JSON（stripe/alipay）或表单/XML（wechat），这里只在
    ``Content-Type`` 含 ``json`` 时按 JSON 解析，其余原样以 ``raw`` 交给插件自行解析。
    响应格式按 provider 分流，与各网关的期望一致。
    """
    content_type = request.headers.get("content-type", "")
    if "json" in content_type:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001 - body 非法 JSON 时按空对象处理，交给插件判失败
            payload = {}
    else:
        raw = (await request.body()).decode("utf-8", "ignore")
        payload = {"raw": raw}
    if not isinstance(payload, dict):
        payload = {"payload": payload}

    result = await payment_flow_service.handle_callback(
        db, provider=provider, payload=payload, headers=dict(request.headers)
    )

    if not result.get("verified"):
        if provider == "alipay":
            return PlainTextResponse("fail")
        if provider == "wechat":
            return JSONResponse({"code": "FAIL", "message": "verify failed"})
        return JSONResponse({"verified": False})

    if provider == "alipay":
        return PlainTextResponse("success")
    if provider == "wechat":
        return JSONResponse({"code": "SUCCESS", "message": "OK"})
    return JSONResponse({"received": True})
