"""
支付网关服务

集成主流支付平台，提供统一的支付接口

功能:
1. Stripe 支付集成
2. PayPal 支付集成
3. 支付宝支付集成
4. 微信支付集成
5. 支付回调处理
6. 订单管理
7. 退款处理
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class PaymentStatus(Enum):
    """支付状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(Enum):
    """支付方式"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    ALIPAY = "alipay"
    WECHAT = "wechat"


class Order:
    """订单"""

    def __init__(
            self,
            order_id: str,
            user_id: int,
            amount: float,
            currency: str = "USD",
            description: str = "",
            payment_method: PaymentMethod = None,
    ):
        self.order_id = order_id
        self.user_id = user_id
        self.amount = amount
        self.currency = currency
        self.description = description
        self.payment_method = payment_method
        self.status = PaymentStatus.PENDING
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.paid_at = None
        self.transaction_id = None
        self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "currency": self.currency,
            "description": self.description,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "paid_at": self.paid_at,
            "transaction_id": self.transaction_id,
            "metadata": self.metadata,
        }


class StripePaymentService:
    """
    Stripe 支付服务
    
    集成 Stripe API 处理支付
    """

    def __init__(self, api_key: str = "", webhook_secret: str = ""):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.base_url = "https://api.stripe.com/v1"

    async def create_payment_intent(
            self,
            order: Order,
            success_url: str,
            cancel_url: str
    ) -> Dict[str, Any]:
        """
        创建支付意图
        
        Args:
            order: 订单对象
            success_url: 成功跳转URL
            cancel_url: 取消跳转URL
            
        Returns:
            支付会话信息
        """
        # TODO: 实际实现需要调用 Stripe API
        # import stripe
        # stripe.api_key = self.api_key

        payment_intent = {
            "id": f"pi_{hashlib.md5(order.order_id.encode()).hexdigest()[:10]}",
            "amount": int(order.amount * 100),  # Stripe uses cents
            "currency": order.currency.lower(),
            "status": "requires_payment_method",
            "client_secret": f"pi_secret_{order.order_id}",
        }

        return {
            "success": True,
            "payment_method": "stripe",
            "payment_intent": payment_intent,
            "checkout_url": f"https://checkout.stripe.com/pay/{payment_intent['client_secret']}",
        }

    async def verify_webhook(self, payload: str, signature: str) -> bool:
        """验证 Webhook 签名"""
        # TODO: 实际实现需要验证 Stripe webhook 签名
        return True

    async def handle_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """处理 Webhook 事件"""
        event_type = event.get("type")

        if event_type == "payment_intent.succeeded":
            return await self._handle_payment_success(event)
        elif event_type == "payment_intent.payment_failed":
            return await self._handle_payment_failure(event)
        elif event_type == "charge.refunded":
            return await self._handle_refund(event)

        return {"success": False, "error": "Unknown event type"}

    async def _handle_payment_success(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """处理支付成功"""
        payment_intent = event.get("data", {}).get("object", {})

        return {
            "success": True,
            "order_id": payment_intent.get("metadata", {}).get("order_id"),
            "transaction_id": payment_intent.get("id"),
            "amount": payment_intent.get("amount") / 100,
            "status": "completed",
        }

    async def _handle_payment_failure(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """处理支付失败"""
        return {
            "success": False,
            "error": "Payment failed",
        }

    async def _handle_refund(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """处理退款"""
        return {
            "success": True,
            "status": "refunded",
        }

    async def refund_payment(
            self,
            transaction_id: str,
            amount: float = None
    ) -> Dict[str, Any]:
        """退款"""
        # TODO: 实际实现需要调用 Stripe API
        return {
            "success": True,
            "refund_id": f"re_{transaction_id}",
            "amount": amount,
            "status": "refunded",
        }


class PayPalPaymentService:
    """
    PayPal 支付服务
    """

    def __init__(self, client_id: str = "", client_secret: str = "", sandbox: bool = True):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.base_url = "https://api-m.sandbox.paypal.com" if sandbox else "https://api-m.paypal.com"

    async def create_order(
            self,
            order: Order,
            return_url: str,
            cancel_url: str
    ) -> Dict[str, Any]:
        """创建 PayPal 订单"""
        # TODO: 实际实现需要调用 PayPal API

        paypal_order = {
            "id": f"PAYID-{order.order_id.upper()}",
            "status": "CREATED",
            "amount": {
                "currency_code": order.currency,
                "value": f"{order.amount:.2f}",
            },
        }

        return {
            "success": True,
            "payment_method": "paypal",
            "order": paypal_order,
            "approval_url": f"https://www.paypal.com/checkoutnow?token={paypal_order['id']}",
        }

    async def capture_payment(self, order_id: str) -> Dict[str, Any]:
        """捕获支付"""
        return {
            "success": True,
            "status": "COMPLETED",
            "transaction_id": f"TXN-{order_id}",
        }

    async def refund_payment(self, transaction_id: str, amount: float = None) -> Dict[str, Any]:
        """退款"""
        return {
            "success": True,
            "refund_id": f"REFUND-{transaction_id}",
            "status": "COMPLETED",
        }


class AlipayPaymentService:
    """
    支付宝支付服务
    """

    def __init__(
            self,
            app_id: str = "",
            private_key: str = "",
            alipay_public_key: str = "",
            sandbox: bool = True
    ):
        self.app_id = app_id
        self.private_key = private_key
        self.alipay_public_key = alipay_public_key
        self.sandbox = sandbox
        self.gateway_url = "https://openapi.alipaydev.com/gateway.do" if sandbox else "https://openapi.alipay.com/gateway.do"

    async def create_payment(
            self,
            order: Order,
            return_url: str,
            notify_url: str
    ) -> Dict[str, Any]:
        """创建支付宝支付"""
        # TODO: 实际实现需要使用 alipay-sdk-python

        payment_params = {
            "out_trade_no": order.order_id,
            "total_amount": f"{order.amount:.2f}",
            "subject": order.description or "商品购买",
            "return_url": return_url,
            "notify_url": notify_url,
        }

        return {
            "success": True,
            "payment_method": "alipay",
            "payment_url": f"{self.gateway_url}?{json.dumps(payment_params)}",
            "qr_code": f"https://qr.alipay.com/{order.order_id}",
        }

    async def verify_notification(self, params: Dict[str, Any]) -> bool:
        """验证异步通知"""
        # TODO: 实际实现需要验证支付宝签名
        return True

    async def refund_payment(self, trade_no: str, amount: float) -> Dict[str, Any]:
        """退款"""
        return {
            "success": True,
            "refund_id": f"REFUND-{trade_no}",
            "status": "SUCCESS",
        }


class WechatPaymentService:
    """
    微信支付服务
    """

    def __init__(
            self,
            app_id: str = "",
            mch_id: str = "",
            api_key: str = "",
            sandbox: bool = True
    ):
        self.app_id = app_id
        self.mch_id = mch_id
        self.api_key = api_key
        self.sandbox = sandbox

    async def create_unified_order(
            self,
            order: Order,
            notify_url: str,
            trade_type: str = "NATIVE"
    ) -> Dict[str, Any]:
        """创建统一下单"""
        # TODO: 实际实现需要调用微信支付 API

        prepay_data = {
            "appid": self.app_id,
            "mch_id": self.mch_id,
            "out_trade_no": order.order_id,
            "total_fee": int(order.amount * 100),  # 单位：分
            "body": order.description or "商品购买",
            "notify_url": notify_url,
            "trade_type": trade_type,
        }

        if trade_type == "NATIVE":
            return {
                "success": True,
                "payment_method": "wechat",
                "code_url": f"weixin://wxpay/bizpayurl?pr={order.order_id}",
                "prepay_id": f"PREPAY-{order.order_id}",
            }
        elif trade_type == "JSAPI":
            return {
                "success": True,
                "payment_method": "wechat",
                "jsapi_params": {},
                "prepay_id": f"PREPAY-{order.order_id}",
            }

        return {"success": False, "error": "Unsupported trade type"}

    async def verify_notification(self, xml_data: str) -> Dict[str, Any]:
        """验证支付通知"""
        # TODO: 实际实现需要解析和验证微信通知
        return {
            "success": True,
            "order_id": "ORDER-123",
            "transaction_id": "TXN-456",
        }

    async def refund_payment(self, transaction_id: str, amount: float) -> Dict[str, Any]:
        """退款"""
        return {
            "success": True,
            "refund_id": f"REFUND-{transaction_id}",
            "status": "SUCCESS",
        }


class PaymentManager:
    """
    支付管理器
    
    统一管理所有支付网关
    """

    def __init__(self):
        self.stripe = StripePaymentService()
        self.paypal = PayPalPaymentService()
        self.alipay = AlipayPaymentService()
        self.wechat = WechatPaymentService()
        self.orders: Dict[str, Order] = {}

    def create_order(
            self,
            user_id: int,
            amount: float,
            currency: str = "USD",
            description: str = "",
            payment_method: PaymentMethod = None
    ) -> Order:
        """创建订单"""
        import uuid
        order_id = f"ORD-{uuid.uuid4().hex[:12].upper()}"

        order = Order(
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            description=description,
            payment_method=payment_method,
        )

        self.orders[order_id] = order
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self.orders.get(order_id)

    async def process_payment(
            self,
            order: Order,
            **kwargs
    ) -> Dict[str, Any]:
        """
        处理支付
        
        Args:
            order: 订单对象
            **kwargs: 支付参数
            
        Returns:
            支付结果
        """
        if order.payment_method == PaymentMethod.STRIPE:
            return await self.stripe.create_payment_intent(order, **kwargs)
        elif order.payment_method == PaymentMethod.PAYPAL:
            return await self.paypal.create_order(order, **kwargs)
        elif order.payment_method == PaymentMethod.ALIPAY:
            return await self.alipay.create_payment(order, **kwargs)
        elif order.payment_method == PaymentMethod.WECHAT:
            return await self.wechat.create_unified_order(order, **kwargs)

        return {"success": False, "error": "Unsupported payment method"}

    async def refund_order(
            self,
            order_id: str,
            amount: float = None
    ) -> Dict[str, Any]:
        """退款"""
        order = self.get_order(order_id)

        if not order:
            return {"success": False, "error": "Order not found"}

        if order.payment_method == PaymentMethod.STRIPE:
            return await self.stripe.refund_payment(order.transaction_id or "", amount)
        elif order.payment_method == PaymentMethod.PAYPAL:
            return await self.paypal.refund_payment(order.transaction_id or "", amount)
        elif order.payment_method == PaymentMethod.ALIPAY:
            return await self.alipay.refund_payment(order.transaction_id or "", amount or order.amount)
        elif order.payment_method == PaymentMethod.WECHAT:
            return await self.wechat.refund_payment(order.transaction_id or "", amount or order.amount)

        return {"success": False, "error": "Unsupported payment method"}


# 全局实例
payment_manager = PaymentManager()
