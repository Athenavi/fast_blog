"""chat.web_push 模块的请求 / 响应模型（Pydantic v2）。

设计约定：

  - 请求模型只暴露订阅端应当提供的字段（``endpoint`` / ``keys``）；服务端强制设定的
    状态字段（``id`` / ``created_at`` / ``send_count`` / ``fail_count`` …）不出现在入参里。
  - 退订接受 ``subscription_id`` 或 ``endpoint``，二者至少其一（服务层校验）。
  - 推送载荷的「展示字段」（``title`` / ``body`` / ``icon`` / ``badge`` / ``data``）与
    v2 payload 结构对齐，由 ``service.build_payload`` 组装。
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import ConfigDict, Field

from src.api.v3.core.base_schema import SchemaBase


class SubscriptionKeys(SchemaBase):
    """浏览器 PushSubscription 的公钥材料（base64url 编码）"""

    p256dh: str = Field(min_length=1, description="客户端公钥（base64url）")
    auth: str = Field(min_length=1, description="客户端认证密钥（base64url）")


class WebPushSubscriptionIn(SchemaBase):
    """登记一条浏览器推送订阅。

    ``endpoint`` 必须是推送服务提供的 https 地址；同一 ``endpoint`` 重复登记视为幂等
    （更新 keys / user_agent，不新增）。
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    endpoint: str = Field(min_length=1, max_length=1000, description="推送服务 endpoint（https）")
    keys: SubscriptionKeys = Field(description="客户端公钥材料")
    user_agent: Optional[str] = Field(default=None, max_length=512, description="登记时的 UA")


class WebPushUnsubscribeIn(SchemaBase):
    """退订：按 ``subscription_id`` 或 ``endpoint`` 精确退订；都不给则退订本人全部订阅。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subscription_id: Optional[str] = Field(default=None, max_length=64, description="订阅 ID")
    endpoint: Optional[str] = Field(default=None, max_length=1000, description="推送 endpoint")


class WebPushSendIn(SchemaBase):
    """向指定用户推送（管理端）。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    user_id: int = Field(description="目标用户 ID")
    title: str = Field(min_length=1, max_length=200, description="通知标题")
    body: str = Field(min_length=1, max_length=2000, description="通知内容")
    icon: Optional[str] = Field(default=None, max_length=500)
    badge: Optional[str] = Field(default=None, max_length=500)
    data: Optional[dict[str, Any]] = Field(default=None, description="附加数据")


class WebPushBroadcastIn(SchemaBase):
    """向**全部已有订阅**的用户广播推送（管理端）。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=2000)
    icon: Optional[str] = Field(default=None, max_length=500)
    badge: Optional[str] = Field(default=None, max_length=500)
    data: Optional[dict[str, Any]] = Field(default=None)
    max_users: int = Field(default=500, ge=1, le=5000, description="单次广播覆盖的用户上限")


class WebPushCleanupIn(SchemaBase):
    """清理失效 / 过期订阅。"""

    model_config = ConfigDict(extra="forbid")

    max_age_days: int = Field(default=30, ge=1, le=3650, description="超过该天数的订阅被清理")
    dry_run: bool = Field(default=False, description="仅统计不删除")


class WebPushSubscriptionOut(SchemaBase):
    """一条订阅（对外只露必要的可读字段，不返回 keys 材料）。"""

    id: str
    endpoint: str
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None
    last_sent_at: Optional[datetime] = None
    send_count: int = 0
    fail_count: int = 0


class WebPushSendResult(SchemaBase):
    """单用户 / 单端点推送的结果明细。"""

    subscription_id: Optional[str] = None
    endpoint: Optional[str] = None
    success: bool = False
    status: Optional[int] = None
    error: Optional[str] = None


class WebPushSendResponse(SchemaBase):
    """一次推送（按用户 / 广播）的汇总结果。"""

    total: int = 0
    sent: int = 0
    failed: int = 0
    pruned: int = 0
    results: list[WebPushSendResult] = Field(default_factory=list)


class WebPushVapidOut(SchemaBase):
    """VAPID 公钥下发。``configured`` 为 False 表示后端尚未配置好推送。"""

    configured: bool = False
    public_key: Optional[str] = None
    subject: Optional[str] = None
    webpush_available: bool = False
    reason: Optional[str] = None


class WebPushStatsOut(SchemaBase):
    """订阅统计（真实从 ``system_settings`` 聚合）。"""

    total_users: int = 0
    total_subscriptions: int = 0
    average_per_user: float = 0.0
    vapid_configured: bool = False
    webpush_available: bool = False


class WebPushCleanupOut(SchemaBase):
    """清理结果。"""

    scanned_users: int = 0
    scanned_subscriptions: int = 0
    removed: int = 0
    dry_run: bool = False
    removed_ids: list[str] = Field(default_factory=list)
