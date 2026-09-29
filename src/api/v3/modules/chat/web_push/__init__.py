"""chat.web_push 模块（接线自 v2 的 ``shared/services/chat/web_push_service.py``）。

一句话定位：**把 Web Push（浏览器推送）订阅登记 / 退订 / 按用户与广播推送 / VAPID 公钥下发 /
订阅与推送统计 / 失效订阅清理**接线为 v3 模块 ``/api/v3/chat/web_push``。

关键落点：

  - 订阅**真实落库**到既有表 ``system_settings``（JSON 配置键
    ``chat.web_push.subscriptions.{user_id}``，每用户一行）。
    **没有**新建 ORM 模型或数据库表 —— 本项目不存在 push 订阅专表，这里复用既有
    ``system_settings`` 的 JSON 配置列，属**如实降级**（详见 ``service.py`` 模块 docstring）。
  - 推送**真实发送**走 ``pywebpush`` + VAPID 密钥（环境变量配置）；依赖库缺失或密钥未配置时
    **如实返回「未配置」错误**，绝不伪造发送成功（v2 也是诚实失败，本模块保持一致）。
  - VAPID 公钥下发 / payload 摘要 / 订阅结构校验 / 失效订阅清理判定均为**纯函数真实计算**。

与 v2 的差异见 ``service.py`` 顶部对照表。
"""

from src.api.v3.modules.chat.web_push.service import (
    DEFAULT_BADGE,
    DEFAULT_ICON,
    PAYLOAD_ACTIONS,
    STORAGE_PREFIX,
    WebPushConfig,
    WebPushService,
    build_payload,
    build_subscription_record,
    cleanup_ids,
    is_expired_subscription,
    is_push_configured,
    is_valid_subscription,
    is_valid_vapid_public_key,
    load_web_push_config,
    payload_digest,
    subscription_issue,
    summarize_subscriptions,
    web_push_service,
)

__all__ = [
    "STORAGE_PREFIX",
    "DEFAULT_ICON",
    "DEFAULT_BADGE",
    "PAYLOAD_ACTIONS",
    "WebPushConfig",
    "WebPushService",
    "web_push_service",
    "load_web_push_config",
    "build_payload",
    "payload_digest",
    "build_subscription_record",
    "subscription_issue",
    "is_valid_subscription",
    "is_valid_vapid_public_key",
    "is_push_configured",
    "is_expired_subscription",
    "cleanup_ids",
    "summarize_subscriptions",
]
