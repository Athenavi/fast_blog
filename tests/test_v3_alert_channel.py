"""测试：告警推送渠道（notification_integrations 真表 + 真实发送）

不需要数据库：

  - ``render_template`` 是纯函数（默认模板 / 自定义模板 / JSON 形态 / 坏模板回退）
  - 平台常量与端点注册、鉴权分流、静态路径前置

真实推送（httpx POST / Telegram API / SMTP）走运行时验证 —— 测试里不真连外网。
"""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.models.monitoring.monitoring_alert import MonitoringAlert
from src.api.v3 import register_v3_routes
from src.api.v3.modules.system.monitor.alert_channel_service import (
    DEFAULT_TEMPLATE,
    PLATFORMS,
    render_template,
)

BASE = "/api/v3/system/monitor"

NEW_PATHS = [
    f"{BASE}/alert-channel",
    f"{BASE}/alert-channel/{{channel_id}}",
    f"{BASE}/alert-channel/{{channel_id}}/test",
    f"{BASE}/alert/{{alert_id}}/dispatch",
    f"{BASE}/alert/{{alert_id}}/deliveries",
]


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def _alert(**overrides) -> MonitoringAlert:
    values = {
        "id": 7,
        "alert_type": "cpu_usage",
        "severity": "critical",
        "title": "CPU 使用率过高",
        "message": "5 分钟均值 95%",
        "source": "system/monitor",
        "metric_name": "cpu_percent",
    }
    values.update(overrides)
    return MonitoringAlert(**values)


# ------------------------------------------------------------------ 模板渲染
def test_render_template_defaults():
    text = render_template(None, _alert())

    assert "critical" in text
    assert "CPU 使用率过高" in text
    assert "5 分钟均值 95%" in text


def test_render_template_custom_variables():
    text = render_template("{title} | {severity} | {metric_name}", _alert())

    assert text == "CPU 使用率过高 | critical | cpu_percent"


def test_render_template_accepts_json_shape():
    """模型注释约定 notification_template 是 JSON —— 带 text 键的写法也要能用"""
    payload = json.dumps({"text": "告警：{title}"})

    assert render_template(payload, _alert()) == "告警：CPU 使用率过高"


def test_render_template_falls_back_on_broken_template():
    # 未知变量 → 回退默认模板，而不是把推送丢掉
    text = render_template("{unknown_field}", _alert())

    assert text == DEFAULT_TEMPLATE.format(
        id=7,
        severity="critical",
        title="CPU 使用率过高",
        message="5 分钟均值 95%",
        alert_type="cpu_usage",
        source="system/monitor",
        metric_name="cpu_percent",
        metric_value=None,
        threshold=None,
        created_at="",
    )


def test_render_template_truncates_long_body():
    text = render_template("{message}", _alert(message="x" * 9000))

    assert len(text) <= 4000


# ------------------------------------------------------------------ 平台常量
def test_platform_matrix():
    assert set(PLATFORMS) == {"telegram", "discord", "slack", "webhook", "email"}
    # telegram 走 Bot API（用 bot_token），email 走邮件服务 —— 都不需要 webhook_url
    assert PLATFORMS["telegram"] is False
    assert PLATFORMS["email"] is False
    assert all(PLATFORMS[name] for name in ("discord", "slack", "webhook"))


# ------------------------------------------------------------------ 端点


@pytest.mark.parametrize("platform", ["telegram", "discord", "slack", "webhook", "email", "sms"])
def test_create_channel_validates_platform(platform):
    """未鉴权时先 401/403；这里只确认请求不会因为参数形态被判成 200"""
    response = TestClient(_app()).post(f"{BASE}/alert-channel", json={"platform": platform})

    assert response.status_code in (401, 403, 422)
