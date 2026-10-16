"""_pending_test_web_push.py —— 待迁入 ``tests/`` 的**纯函数**单测

**说明**：本任务的环境禁止写 ``tests/`` 目录、禁止执行 shell，因此把 web_push 模块的纯函数单测
临时放在模块目录内（文件名以下划线开头，不会被当作业务模块导入）。父代理恢复后应把它移动到
``tests/test_v3_web_push.py``（或 ``tests/api/v3/chat/test_web_push.py``）。

只覆盖**不依赖 DB / 网络 / FastAPI / 时钟**的纯函数：:

  - ``is_valid_vapid_public_key``    VAPID 公钥形状校验
  - ``is_push_configured``           发送前置条件（库可用 + 公私钥齐全）
  - ``subscription_issue`` / ``is_valid_subscription``  订阅结构校验
  - ``build_subscription_record``    落库记录构造（字段收敛 + UA 截断）
  - ``build_payload`` / ``payload_digest``   通知载荷与稳定摘要
  - ``subscription_age_days`` / ``is_expired_subscription`` / ``cleanup_ids``  过期与清理判定
  - ``summarize_subscriptions``      订阅统计

运行（在仓库根目录，确保可 ``import src.*``）::

    python -m pytest src/api/v3/modules/chat/web_push/_pending_test_web_push.py -q

**本文件尚未运行**：本任务执行环境不允许跑 pytest，故仅静态编写；断言逐行对照 ``service.py`` 实现。
"""

import base64
from datetime import datetime

from src.api.v3.modules.chat.web_push.service import (
    DEFAULT_BADGE,
    DEFAULT_ICON,
    PAYLOAD_ACTIONS,
    build_payload,
    build_subscription_record,
    cleanup_ids,
    is_expired_subscription,
    is_push_configured,
    is_valid_subscription,
    is_valid_vapid_public_key,
    payload_digest,
    subscription_age_days,
    subscription_issue,
    summarize_subscriptions,
)


# ------------------------------------------------------------------ 辅助
def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _vapid_key(*, length: int = 65, first: int = 0x04) -> str:
    """构造一段 base64url 的 uncompressed 公钥（首字节默认 0x04）"""
    return _b64url(bytes([first]) + bytes(max(length - 1, 0)))


def _record(**overrides) -> dict:
    base = {
        "id": "abc123",
        "endpoint": "https://push.example.com/abc",
        "keys": {"p256dh": "p256dh-value", "auth": "auth-value"},
        "user_agent": "UA",
        "created_at": "2026-01-01T00:00:00",
        "last_sent_at": None,
        "send_count": 0,
        "fail_count": 0,
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------ VAPID 公钥
def test_valid_vapid_public_key_shape():
    # 65 字节 + 首字节 0x04 → 合法
    assert is_valid_vapid_public_key(_vapid_key()) is True


def test_invalid_vapid_public_key_wrong_prefix():
    # 首字节非 0x04
    assert is_valid_vapid_public_key(_vapid_key(first=0x05)) is False


def test_invalid_vapid_public_key_wrong_length():
    assert is_valid_vapid_public_key(_vapid_key(length=64)) is False
    assert is_valid_vapid_public_key(_vapid_key(length=66)) is False


def test_invalid_vapid_public_key_empty_or_none():
    assert is_valid_vapid_public_key(None) is False
    assert is_valid_vapid_public_key("") is False
    assert is_valid_vapid_public_key("!!!not-base64!!!") is False


# -------------------------------------------------------- 发送前置条件
def test_is_push_configured_requires_all():
    assert is_push_configured("pub", "priv", webpush_available=True) is True
    # 缺库
    assert is_push_configured("pub", "priv", webpush_available=False) is False
    # 缺私钥
    assert is_push_configured("pub", "", webpush_available=True) is False
    # 缺公钥
    assert is_push_configured("", "priv", webpush_available=True) is False


# ------------------------------------------------------------ 订阅结构校验
def test_subscription_issue_none_for_valid():
    assert subscription_issue(_record()) is None
    assert is_valid_subscription(_record()) is True


def test_subscription_issue_not_a_dict():
    assert subscription_issue(["nope"]) == "订阅数据必须是 JSON 对象"
    assert is_valid_subscription(None) is False


def test_subscription_issue_endpoint():
    assert subscription_issue(_record(endpoint="")) == "缺少 endpoint"
    assert subscription_issue(_record(endpoint="http://push.example.com")) == "endpoint 必须是 https 地址"


def test_subscription_issue_keys():
    assert subscription_issue(_record(keys=None)) == "缺少订阅 keys"
    assert subscription_issue(_record(keys={"auth": "a"})) == "缺少 keys.p256dh"
    assert subscription_issue(_record(keys={"p256dh": "p"})) == "缺少 keys.auth"
    assert subscription_issue(_record(keys={"p256dh": "", "auth": "a"})) == "缺少 keys.p256dh"


# ------------------------------------------------------------ 记录构造
def test_build_subscription_record_fields():
    record = build_subscription_record(
        _record(),
        subscription_id="sid-1",
        now_iso="2026-02-02T03:04:05",
        user_agent="MyUA",
    )
    assert record["id"] == "sid-1"
    assert record["endpoint"] == "https://push.example.com/abc"
    assert record["keys"] == {"p256dh": "p256dh-value", "auth": "auth-value"}
    assert record["user_agent"] == "MyUA"
    assert record["created_at"] == "2026-02-02T03:04:05"
    assert record["last_sent_at"] is None
    assert record["send_count"] == 0
    assert record["fail_count"] == 0


def test_build_subscription_record_user_agent_truncated():
    record = build_subscription_record(
        _record(), subscription_id="sid", now_iso="2026-01-01T00:00:00", user_agent="x" * 600
    )
    assert len(record["user_agent"]) == 512


# ------------------------------------------------------------ 载荷与摘要
def test_build_payload_defaults_and_injected_time():
    payload = build_payload("标题", "正文", timestamp="2026-03-03T00:00:00")
    assert payload["title"] == "标题"
    assert payload["body"] == "正文"
    assert payload["icon"] == DEFAULT_ICON
    assert payload["badge"] == DEFAULT_BADGE
    assert payload["data"] == {}
    assert payload["timestamp"] == "2026-03-03T00:00:00"
    assert payload["actions"] == [dict(a) for a in PAYLOAD_ACTIONS]


def test_build_payload_overrides():
    payload = build_payload(
        "t", "b", icon="/i.png", badge="/b.png", data={"k": 1}, timestamp="ts"
    )
    assert payload["icon"] == "/i.png"
    assert payload["badge"] == "/b.png"
    assert payload["data"] == {"k": 1}


def test_payload_digest_is_stable_under_key_order():
    a = {"title": "t", "data": {"x": 1, "y": 2}}
    b = {"data": {"y": 2, "x": 1}, "title": "t"}
    assert payload_digest(a) == payload_digest(b)
    # 长度是 sha256 的十六进制
    assert len(payload_digest(a)) == 64


def test_payload_digest_changes_with_content():
    assert payload_digest({"title": "a"}) != payload_digest({"title": "b"})


# ------------------------------------------------------------ 过期 / 清理
def test_subscription_age_days_injected_now():
    now = datetime(2026, 1, 11)
    assert subscription_age_days(_record(created_at="2026-01-01T00:00:00"), now) == 10.0
    # 无法解析 → None
    assert subscription_age_days(_record(created_at="not-a-date"), now) is None
    assert subscription_age_days(_record(created_at=None), now) is None


def test_is_expired_subscription_boundary():
    now = datetime(2026, 1, 11)
    record = _record(created_at="2026-01-01T00:00:00")  # 10 天
    # 严格大于：10 > 10 为假，10 > 5 为真
    assert is_expired_subscription(record, now, 10) is False
    assert is_expired_subscription(record, now, 5) is True


def test_cleanup_ids_expired_and_invalid():
    now = datetime(2026, 1, 31)
    records = [
        _record(id="fresh", created_at="2026-01-30T00:00:00"),  # 1 天，合法 → 保留
        _record(id="old", created_at="2025-01-01T00:00:00"),  # 过期 → 清理
        _record(id="bad", endpoint="http://x", created_at="2026-01-30T00:00:00"),  # 非法 → 清理
    ]
    removable = cleanup_ids(records, now, 30)
    assert set(removable) == {"old", "bad"}


def test_cleanup_ids_skips_records_without_id():
    now = datetime(2026, 1, 31)
    records = [{"created_at": "2000-01-01T00:00:00"}, _record(id=None)]
    assert cleanup_ids(records, now, 30) == []


# ------------------------------------------------------------ 统计
def test_summarize_subscriptions():
    per_user = {
        1: [_record(id="a"), _record(id="b")],
        2: [_record(id="c")],
    }
    summary = summarize_subscriptions(per_user)
    assert summary["total_users"] == 2
    assert summary["total_subscriptions"] == 3
    assert summary["average_per_user"] == 1.5


def test_summarize_subscriptions_empty():
    summary = summarize_subscriptions({})
    assert summary == {"total_users": 0, "total_subscriptions": 0, "average_per_user": 0.0}
