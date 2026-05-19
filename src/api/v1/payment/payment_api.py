"""
支付网关 API

提供支付、退款、订单查询等功能
"""

from typing import Optional

from fastapi import APIRouter, Depends, Body

from shared.services.payment.payment_gateway import (
    payment_manager,
    PaymentMethod,
)
from src.api.v1.core.responses import ApiResponse
from src.api.v1.users.user_management import jwt_required

router = APIRouter(prefix="/payment", tags=["Payment Gateway"])


@router.post("/create-order")
async def create_order(
        amount: float = Body(..., description="金额"),
        currency: str = Body("USD", description="货币"),
        description: str = Body("", description="描述"),
        payment_method: str = Body(..., description="支付方式 (stripe/paypal/alipay/wechat)"),
        current_user=Depends(jwt_required)
):
    """
    创建订单
    
    生成新的支付订单
    """
    try:
        method_enum = PaymentMethod(payment_method)

        order = payment_manager.create_order(
            user_id=current_user.id,
            amount=amount,
            currency=currency,
            description=description,
            payment_method=method_enum,
        )

        return ApiResponse(
            success=True,
            data=order.to_dict()
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e)
        )


@router.post("/pay/{order_id}")
async def process_payment(
        order_id: str,
        success_url: str = Body(..., description="成功跳转URL"),
        cancel_url: str = Body(..., description="取消跳转URL"),
        notify_url: str = Body("", description="通知URL"),
        current_user=Depends(jwt_required)
):
    """
    处理支付
    
    根据订单创建支付会话
    """
    order = payment_manager.get_order(order_id)

    if not order:
        return ApiResponse(
            success=False,
            error="Order not found"
        )

    try:
        result = await payment_manager.process_payment(
            order=order,
            success_url=success_url,
            cancel_url=cancel_url,
            notify_url=notify_url,
        )

        return ApiResponse(
            success=result.get("success", False),
            data=result
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e)
        )


@router.get("/order/{order_id}")
async def get_order(
        order_id: str,
        current_user=Depends(jwt_required)
):
    """
    查询订单
    
    获取订单详细信息
    """
    order = payment_manager.get_order(order_id)

    if not order:
        return ApiResponse(
            success=False,
            error="Order not found"
        )

    return ApiResponse(
        success=True,
        data=order.to_dict()
    )


@router.post("/refund/{order_id}")
async def refund_order(
        order_id: str,
        amount: Optional[float] = Body(None, description="退款金额（不填则全额退款）"),
        reason: str = Body("", description="退款原因"),
        current_user=Depends(jwt_required)
):
    """
    退款
    
    对已支付的订单进行退款
    """
    try:
        result = await payment_manager.refund_order(order_id, amount)

        return ApiResponse(
            success=result.get("success", False),
            data=result
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e)
        )


@router.post("/webhook/stripe")
async def stripe_webhook(
        payload: str = Body(...),
        signature: str = Body(..., description="Stripe签名")
):
    """
    Stripe Webhook
    
    接收 Stripe 支付事件通知
    """
    # 验证 webhook
    is_valid = await payment_manager.stripe.verify_webhook(payload, signature)

    if not is_valid:
        return ApiResponse(
            success=False,
            error="Invalid signature"
        )

    # 处理事件
    import json
    event = json.loads(payload)
    result = await payment_manager.stripe.handle_webhook_event(event)

    return ApiResponse(
        success=result.get("success", False),
        data=result
    )


@router.post("/webhook/paypal")
async def paypal_webhook(
        event_data: dict = Body(...)
):
    """
    PayPal Webhook
    
    接收 PayPal 支付事件通知
    """
    # TODO: 实现 PayPal webhook 处理
    return ApiResponse(
        success=True,
        message="Webhook received"
    )


@router.post("/webhook/alipay")
async def alipay_webhook(
        params: dict = Body(...)
):
    """
    支付宝异步通知
    
    接收支付宝支付结果通知
    """
    # 验证通知
    is_valid = await payment_manager.alipay.verify_notification(params)

    if not is_valid:
        return ApiResponse(
            success=False,
            error="Invalid notification"
        )

    # TODO: 更新订单状态

    return ApiResponse(
        success=True,
        message="Notification verified"
    )


@router.post("/webhook/wechat")
async def wechat_webhook(
        xml_data: str = Body(...)
):
    """
    微信支付通知
    
    接收微信支付结果通知
    """
    # 验证通知
    result = await payment_manager.wechat.verify_notification(xml_data)

    return ApiResponse(
        success=result.get("success", False),
        data=result
    )


@router.get("/methods")
async def get_payment_methods(current_user=Depends(jwt_required)):
    """
    获取支持的支付方式
    
    列出所有可用的支付网关
    """
    methods = [
        {
            "id": "stripe",
            "name": "Stripe",
            "description": "信用卡支付",
            "currencies": ["USD", "EUR", "GBP"],
            "icon": "credit-card",
        },
        {
            "id": "paypal",
            "name": "PayPal",
            "description": "PayPal 账户支付",
            "currencies": ["USD", "EUR", "GBP", "JPY"],
            "icon": "paypal",
        },
        {
            "id": "alipay",
            "name": "支付宝",
            "description": "支付宝扫码支付",
            "currencies": ["CNY"],
            "icon": "alipay",
        },
        {
            "id": "wechat",
            "name": "微信支付",
            "description": "微信扫码支付",
            "currencies": ["CNY"],
            "icon": "wechat",
        },
    ]

    return ApiResponse(
        success=True,
        data={
            "methods": methods,
            "total": len(methods)
        }
    )


@router.get("/guide")
async def get_payment_guide(current_user=Depends(jwt_required)):
    """
    获取支付集成指南
    """
    guide = {
        "overview": {
            "title": "支付网关集成",
            "description": "支持多种主流支付方式，提供安全便捷的支付体验。",
            "version": "1.0.0"
        },
        "supported_methods": [
            {
                "name": "Stripe",
                "description": "全球领先的在线支付平台",
                "features": ["信用卡", "借记卡", "Apple Pay", "Google Pay"],
                "setup": "需要注册 Stripe 账号并获取 API Key"
            },
            {
                "name": "PayPal",
                "description": "国际知名的电子钱包",
                "features": ["PayPal账户", "信用卡", "国际支付"],
                "setup": "需要注册 PayPal Business 账号"
            },
            {
                "name": "支付宝",
                "description": "中国最大的移动支付平台",
                "features": ["扫码支付", "APP支付", "网页支付"],
                "setup": "需要申请支付宝开放平台账号"
            },
            {
                "name": "微信支付",
                "description": "腾讯旗下的移动支付服务",
                "features": ["扫码支付", "公众号支付", "APP支付"],
                "setup": "需要注册微信商户平台"
            }
        ],
        "integration_steps": [
            "1. 配置支付网关的 API 密钥",
            "2. 创建订单: POST /payment/create-order",
            "3. 发起支付: POST /payment/pay/{order_id}",
            "4. 接收回调: 配置 Webhook URL",
            "5. 处理结果: 更新订单状态"
        ],
        "security": [
            "使用 HTTPS 传输",
            "验证 Webhook 签名",
            "不要在前端暴露私钥",
            "实施防重放攻击",
            "记录所有交易日志"
        ],
        "api_endpoints": {
            "create_order": "POST /payment/create-order - 创建订单",
            "process_payment": "POST /payment/pay/{order_id} - 处理支付",
            "get_order": "GET /payment/order/{order_id} - 查询订单",
            "refund": "POST /payment/refund/{order_id} - 退款",
            "webhooks": "POST /payment/webhook/{provider} - Webhook 回调"
        }
    }

    return ApiResponse(
        success=True,
        data=guide
    )
