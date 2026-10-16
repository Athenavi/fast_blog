"""
SMS Provider Plugin
==================
短信服务提供商插件 — 支持阿里云、腾讯云、Twilio。

核心 sms_verification_service 通过 PluginManager 查找具备
"send:custom:sms" 能力的激活插件，委派实际短信发送。

激活后通过 /api/v2/plugins/sms-provider/action 调用 send_sms 方法。
"""

import logging

from shared.services.plugins.plugin_manager.core import BasePlugin

logger = logging.getLogger(__name__)


class SmsProviderPlugin(BasePlugin):
    """短信服务提供商插件"""

    def __init__(self):
        super().__init__(
            plugin_id=2002,
            name="SMS Provider",
            slug="sms-provider",
            version="1.0.0",
            description="短信服务提供商插件 — 支持阿里云、腾讯云、Twilio",
            author="FastBlog Team",
            author_url="https://athenavi.github.io",
        )

    def register_hooks(self):
        """注册钩子"""
        pass

    def subscribers(self) -> list:
        """EventBus 订阅"""
        return []

    # ─── 核心方法：核心服务委派入口 ───────────────

    def send_sms(self, phone: str, code: str) -> bool:
        """
        发送短信验证码（核心服务委派入口）

        根据 plugin settings 中的 provider 配置选择服务商。
        所有 provider 均未配置凭据时返回 False（不静默 mock）。

        Args:
            phone: 手机号
            code: 验证码

        Returns:
            是否发送成功
        """
        provider = self.settings.get("provider", "")

        if provider == "aliyun":
            return self._send_aliyun(phone, code)
        elif provider == "tencent":
            return self._send_tencent(phone, code)
        elif provider == "twilio":
            return self._send_twilio(phone, code)
        else:
            logger.error(f"SMS plugin: no provider configured (got '{provider}'), send FAILED")
            return False

    # ─── 阿里云 ──────────────────────────────────

    def _send_aliyun(self, phone: str, code: str) -> bool:
        """阿里云短信"""
        key_id = self.settings.get("aliyun_access_key_id", "")
        key_secret = self.settings.get("aliyun_access_key_secret", "")
        sign_name = self.settings.get("aliyun_sign_name", "")
        template_code = self.settings.get("aliyun_template_code", "")

        if not all([key_id, key_secret, sign_name, template_code]):
            logger.error("Aliyun SMS config incomplete, send FAILED")
            return False

        try:
            from aliyun_python_sdk_dysmsapi20170525.client import Client
            from aliyun_python_sdk_tea_util.models import RuntimeOptions
            import aliyun_python_sdk_dysmsapi20170525.models as dysms_models
            from alibabacloud_tea_openapi.models import Config as OpenApiConfig
        except ImportError:
            try:
                # 兼容旧版 SDK 包名
                from dysms_python_dysmsapi.client import AcsClient
                from dysms_python_dysmsapi.request import SmsRequest
            except ImportError:
                logger.error("Aliyun SMS SDK not installed, send FAILED")
                return False
            return self._send_aliyun_legacy(phone, code, key_id, key_secret, sign_name, template_code)

        try:
            config = OpenApiConfig(
                access_key_id=key_id,
                access_key_secret=key_secret,
                endpoint="dysmsapi.aliyuncs.com",
            )
            client = Client(config)
            params = dysms_models.SendMessageToGlobeRequest(
                to_number=phone,
                from_number=sign_name,
                message=f"verification code: {code}",
                type="OTP",
            )
            resp = client.send_message_to_globe(params, RuntimeOptions())
            logger.info(f"Aliyun SMS sent to {phone}, response code: {resp.body.response_code}")
            return True
        except Exception as e:
            logger.error(f"Aliyun SMS failed: {e}")
            return False

    def _send_aliyun_legacy(self, phone, code, key_id, key_secret, sign_name, template_code):
        """阿里云旧版 SDK"""
        try:
            from dysms_python_dysmsapi.acs_client import AcsClient
            from dysms_python_dysmsapi.request import SmsRequest

            client = AcsClient(key_id, key_secret, "cn-hangzhou")
            req = SmsRequest()
            req.set_accept_format("json")
            req.set_PhoneNumbers(phone)
            req.set_SignName(sign_name)
            req.set_TemplateCode(template_code)
            req.set_TemplateParam(f'{{"code":"{code}"}}')
            resp = client.do_action_with_exception(req)
            logger.info(f"Aliyun SMS (legacy) sent to {phone}")
            return True
        except Exception as e:
            logger.error(f"Aliyun SMS (legacy) failed: {e}")
            return False

    # ─── 腾讯云 ──────────────────────────────────

    def _send_tencent(self, phone: str, code: str) -> bool:
        """腾讯云短信"""
        secret_id = self.settings.get("tencent_secret_id", "")
        secret_key = self.settings.get("tencent_secret_key", "")
        app_id = self.settings.get("tencent_app_id", "")
        sign_name = self.settings.get("tencent_sign_name", "")
        template_id = self.settings.get("tencent_template_id", "")

        if not all([secret_id, secret_key, app_id, sign_name, template_id]):
            logger.error("Tencent SMS config incomplete, send FAILED")
            return False

        try:
            from qcloudsms_py import SmsSingleSender
            from qcloudsms_py.httpclient import HTTPError

            ssender = SmsSingleSender(app_id, sign_name, secret_id, secret_key)
            params = [code]
            resp = ssender.send_with_param("86", phone, template_id, params, sign=sign_name)
            logger.info(f"Tencent SMS sent to {phone}, result: {resp}")
            return True
        except ImportError:
            logger.error("Tencent SMS SDK not installed (pip install qcloudsms_py), send FAILED")
            return False
        except HTTPError as e:
            logger.error(f"Tencent SMS HTTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Tencent SMS failed: {e}")
            return False

    # ─── Twilio ───────────────────────────────────

    def _send_twilio(self, phone: str, code: str) -> bool:
        """Twilio 短信"""
        account_sid = self.settings.get("twilio_account_sid", "")
        auth_token = self.settings.get("twilio_auth_token", "")
        from_number = self.settings.get("twilio_from_number", "")

        if not all([account_sid, auth_token, from_number]):
            logger.error("Twilio SMS config incomplete, send FAILED")
            return False

        try:
            from twilio.rest import Client

            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=f"Your verification code is: {code}",
                from_=from_number,
                to=phone,
            )
            if message.sid:
                logger.info(f"Twilio SMS sent to {phone}, SID: {message.sid}")
                return True
            else:
                logger.error("Twilio SMS failed: No message SID returned")
                return False
        except ImportError:
            logger.error("Twilio SDK not installed (pip install twilio), send FAILED")
            return False
        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            return False


# 模块级实例（插件系统通过此变量发现）
plugin_instance = SmsProviderPlugin()
