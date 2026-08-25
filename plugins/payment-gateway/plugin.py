"""
Payment Gateway Plugin
=====================
支付网关插件 — 支持支付宝、微信支付、Stripe。

核心 payment_management.py 通过 PluginManager 查找具备
"execute:custom:payment" 能力的激活插件，委派支付发起与回调验签。
成功态（succeeded/completed/paid）只能由本插件的回调验签流程产生，
禁止管理员手动设置。
"""

import hashlib
import hmac
import logging

from shared.services.plugins.plugin_manager.core import BasePlugin

logger = logging.getLogger(__name__)


class PaymentGatewayPlugin(BasePlugin):
    """支付网关插件"""

    def __init__(self):
        super().__init__(
            plugin_id=2002,
            name="Payment Gateway",
            slug="payment-gateway",
            version="1.0.0",
            description="支付网关插件 — 支持支付宝、微信支付、Stripe",
            author="FastBlog Team",
            author_url="https://athenavi.github.io",
        )

    def register_hooks(self):
        pass

    def subscribers(self) -> list:
        return []

    # ─── 核心方法 ─────────────────────────────────

    def create_payment(self, order_id: str, amount: int, subject: str = "",
                       user_id: int = None, **kwargs) -> dict:
        """
        发起支付（核心服务委派入口）

        Args:
            order_id: 业务订单号
            amount: 金额（分）
            subject: 订单标题
            user_id: 用户ID
            **kwargs: 额外参数

        Returns:
            dict: {success, provider, payment_url/cashier_id, transaction_id}
        """
        provider = self.settings.get("provider", "")

        if provider == "alipay":
            return self._create_alipay(order_id, amount, subject, **kwargs)
        elif provider == "wechat":
            return self._create_wechat(order_id, amount, subject, **kwargs)
        elif provider == "stripe":
            return self._create_stripe(order_id, amount, subject, **kwargs)
        else:
            logger.error(f"Payment plugin: no provider configured (got '{provider}')")
            return {"success": False, "error": "No payment provider configured"}

    def verify_callback(self, provider: str, payload: dict, headers: dict = None) -> dict:
        """
        验证支付回调签名（核心服务委派入口）

        只有通过此方法的回调才能将交易状态更新为 succeeded。

        Args:
            provider: 回调来源（alipay/wechat/stripe）
            payload: 回调数据
            headers: HTTP 头

        Returns:
            dict: {verified, order_id, transaction_id, amount, status}
        """
        if provider == "alipay":
            return self._verify_alipay(payload)
        elif provider == "wechat":
            return self._verify_wechat(payload)
        elif provider == "stripe":
            return self._verify_stripe(payload, headers or {})
        else:
            logger.error(f"Unknown callback provider: {provider}")
            return {"verified": False, "error": "Unknown provider"}

    # ─── 支付宝 ──────────────────────────────────

    def _create_alipay(self, order_id, amount, subject, **kwargs):
        key_id = self.settings.get("alipay_app_id", "")
        sandbox = self.settings.get("alipay_sandbox", True)

        if not key_id:
            return {"success": False, "error": "Alipay config incomplete"}

        try:
            from alipay_sdk import AliPay
        except ImportError:
            logger.error("alipay-sdk-python not installed (pip install alipay-sdk-python)")
            return {"success": False, "error": "Alipay SDK not installed"}

        try:
            gateway = "https://openapi-sandbox.dl.alipaydev.com/gateway.do" if sandbox else "https://openapi.alipay.com/gateway.do"
            alipay = AliPay(
                appid=key_id,
                app_notify_url=kwargs.get("notify_url", ""),
                app_private_key_string=self.settings.get("alipay_private_key", ""),
                alipay_public_key_string=self.settings.get("alipay_public_key", ""),
                sign_type="RSA2",
                debug=sandbox,
            )
            url = alipay.api_alipay_trade_page_pay(
                out_trade_no=order_id,
                total_amount=f"{amount / 100:.2f}",
                subject=subject or order_id,
                return_url=kwargs.get("return_url", ""),
                notify_url=kwargs.get("notify_url", ""),
            )
            return {"success": True, "provider": "alipay", "payment_url": gateway + "?" + url}
        except Exception as e:
            logger.error(f"Alipay create payment failed: {e}")
            return {"success": False, "error": str(e)}

    def _verify_alipay(self, payload):
        try:
            from alipay_sdk import AliPay
            alipay = AliPay(
                appid=self.settings.get("alipay_app_id", ""),
                app_private_key_string=self.settings.get("alipay_private_key", ""),
                alipay_public_key_string=self.settings.get("alipay_public_key", ""),
                sign_type="RSA2",
            )
            sig_verified = alipay.verify(payload, payload.pop("sign", ""), payload.pop("sign_type", "RSA2"))
            if not sig_verified:
                return {"verified": False, "error": "Signature verification failed"}

            return {
                "verified": True,
                "order_id": payload.get("out_trade_no"),
                "transaction_id": payload.get("trade_no"),
                "amount": int(float(payload.get("total_amount", 0)) * 100),
                "status": "succeeded" if payload.get("trade_status") == "TRADE_SUCCESS" else "failed",
            }
        except ImportError:
            logger.error("alipay-sdk-python not installed")
            return {"verified": False, "error": "Alipay SDK not installed"}
        except Exception as e:
            logger.error(f"Alipay callback verification failed: {e}")
            return {"verified": False, "error": str(e)}

    # ─── 微信支付 ────────────────────────────────

    def _create_wechat(self, order_id, amount, subject, **kwargs):
        app_id = self.settings.get("wechat_app_id", "")
        mch_id = self.settings.get("wechat_mch_id", "")
        api_key = self.settings.get("wechat_api_key", "")

        if not all([app_id, mch_id, api_key]):
            return {"success": False, "error": "WeChat config incomplete"}

        try:
            import requests

            notify_url = self.settings.get("wechat_notify_url", "") or kwargs.get("notify_url", "")
            xml_data = self._build_wechat_xml(app_id, mch_id, order_id, amount, subject or "Order", notify_url, api_key)
            resp = requests.post("https://api.mch.weixin.qq.com/pay/unifiedorder", data=xml_data.encode("utf-8"),
                                 timeout=10)
            result = self._parse_wechat_xml(resp.text)
            if result.get("return_code") == "SUCCESS" and result.get("prepay_id"):
                return {"success": True, "provider": "wechat", "prepay_id": result["prepay_id"]}
            else:
                return {"success": False, "error": result.get("return_msg", "Unknown error")}
        except Exception as e:
            logger.error(f"WeChat create payment failed: {e}")
            return {"success": False, "error": str(e)}

    def _verify_wechat(self, payload):
        api_key = self.settings.get("wechat_api_key", "")
        try:
            sign = payload.get("sign", "")
            calc_sign = self._sign_wechat(payload, api_key)
            if sign != calc_sign:
                return {"verified": False, "error": "Signature mismatch"}

            return {
                "verified": True,
                "order_id": payload.get("out_trade_no"),
                "transaction_id": payload.get("transaction_id"),
                "amount": int(payload.get("total_fee", 0)),
                "status": "succeeded" if payload.get("result_code") == "SUCCESS" else "failed",
            }
        except Exception as e:
            logger.error(f"WeChat callback verification failed: {e}")
            return {"verified": False, "error": str(e)}

    def _build_wechat_xml(self, app_id, mch_id, order_id, amount, body, notify_url, api_key):
        import secrets
        params = {
            "appid": app_id,
            "mch_id": mch_id,
            "nonce_str": secrets.token_hex(16),  # 使用安全的随机数生成 nonce
            "body": body,
            "out_trade_no": order_id,
            "total_fee": str(amount),
            "spbill_create_ip": "127.0.0.1",
            "notify_url": notify_url,
            "trade_type": "NATIVE",
        }
        params["sign"] = self._sign_wechat(params, api_key)
        xml = "<xml>" + "".join(f"<{k}>{v}</{k}>" for k, v in params.items()) + "</xml>"
        return xml

    @staticmethod
    def _sign_wechat(params, api_key):
        sorted_items = sorted((k, v) for k, v in params.items() if k != "sign" and v)
        string_a = "&".join(f"{k}={v}" for k, v in sorted_items) + f"&key={api_key}"
        # 微信官方推荐 HMAC-SHA256（微信 APIv3 强制要求）
        return hmac.new(api_key.encode("utf-8"), string_a.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    @staticmethod
    def _parse_wechat_xml(xml_text):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_text)
        return {child.tag: child.text for child in root}

    # ─── Stripe ───────────────────────────────────

    def _create_stripe(self, order_id, amount, subject, **kwargs):
        secret_key = self.settings.get("stripe_secret_key", "")
        if not secret_key:
            return {"success": False, "error": "Stripe config incomplete"}

        try:
            import stripe
            stripe.api_key = secret_key
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": self.settings.get("currency", "cny"),
                        "product_data": {"name": subject or order_id},
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=kwargs.get("return_url", ""),
                cancel_url=kwargs.get("cancel_url", ""),
                client_reference_id=order_id,
            )
            return {"success": True, "provider": "stripe", "payment_url": session.url, "transaction_id": session.id}
        except ImportError:
            logger.error("stripe not installed (pip install stripe)")
            return {"success": False, "error": "Stripe SDK not installed"}
        except Exception as e:
            logger.error(f"Stripe create payment failed: {e}")
            return {"success": False, "error": str(e)}

    def _verify_stripe(self, payload, headers):
        webhook_secret = self.settings.get("stripe_webhook_secret", "")
        try:
            import stripe
            stripe.api_key = self.settings.get("stripe_secret_key", "")
            sig_header = headers.get("Stripe-Signature", "")
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret) if webhook_secret else None
            if event is None:
                return {"verified": False, "error": "Webhook secret not configured or invalid payload"}

            obj = event["data"]["object"]
            return {
                "verified": True,
                "order_id": obj.get("client_reference_id"),
                "transaction_id": obj.get("id"),
                "amount": obj.get("amount_total", 0),
                "status": "succeeded" if obj.get("payment_status") == "paid" else "failed",
            }
        except ImportError:
            logger.error("stripe not installed")
            return {"verified": False, "error": "Stripe SDK not installed"}
        except Exception as e:
            logger.error(f"Stripe callback verification failed: {e}")
            return {"verified": False, "error": str(e)}


# 模块级实例
plugin_instance = PaymentGatewayPlugin()
