"""测试：埋点上报与阅读聚合

不需要数据库：

  - ``parse_user_agent`` 与 ``_trim`` 是纯函数（UA 解析不引第三方库，用轻量正则）
  - 全部端点注册与**读端点**的鉴权分流
  - 上报端点走可选登录（无 token 也应进入业务逻辑，因此不能用 401 判定）

真实写入（四张表）与聚合结果走运行时验证。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v3 import register_v3_routes
from src.api.v3.modules.analytics.tracking.service import _trim, parse_user_agent

WRITE_PATHS = [
    "/api/v3/analytics/tracking/page-view",
    "/api/v3/analytics/tracking/event",
    "/api/v3/analytics/tracking/search",
    "/api/v3/analytics/tracking/ad-impression",
    "/api/v3/analytics/tracking/ad-click",
]

READ_PATHS = [
    "/api/v3/analytics/tracking/traffic-sources",
    "/api/v3/analytics/tracking/devices",
    "/api/v3/analytics/tracking/popular-pages",
    "/api/v3/analytics/tracking/sessions",
    "/api/v3/analytics/tracking/articles/{article_id}",
    "/api/v3/analytics/tracking/searches",
    "/api/v3/analytics/tracking/ads",
]


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ UA 解析
def test_parse_user_agent_desktop_chrome():
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )

    parsed = parse_user_agent(ua)

    assert parsed["device_type"] == "desktop"
    assert parsed["browser"] == "Chrome"
    assert parsed["platform"] == "Windows"


def test_parse_user_agent_iphone_safari():
    ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"

    parsed = parse_user_agent(ua)

    assert parsed["device_type"] == "mobile"
    assert parsed["browser"] == "Safari"
    assert parsed["platform"] == "iOS"


def test_parse_user_agent_ipad_is_tablet():
    ua = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"

    assert parse_user_agent(ua)["device_type"] == "tablet"


def test_parse_user_agent_wechat_is_detected():
    ua = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 MicroMessenger/8.0 Mobile Safari/537.36"

    parsed = parse_user_agent(ua)

    assert parsed["device_type"] == "mobile"
    assert parsed["browser"] == "WeChat"
    assert parsed["platform"] == "Android"


def test_parse_user_agent_bot_is_detected():
    assert parse_user_agent("python-requests/2.31")["browser"] == "Bot"


def test_parse_user_agent_empty_returns_nulls():
    assert parse_user_agent(None) == {"device_type": None, "browser": None, "platform": None}
    assert parse_user_agent("") == {"device_type": None, "browser": None, "platform": None}


def test_trim_truncates_and_passes_none():
    assert _trim(None, 10) is None
    assert _trim("abcdef", 3) == "abc"
    assert _trim("abc", 10) == "abc"


# ------------------------------------------------------------------ 端点


@pytest.mark.parametrize("path", WRITE_PATHS)
def test_write_endpoints_do_not_require_auth(path):
    """上报端点走可选登录：未登录也应进入业务（空体 → 422，而不是 401）"""
    response = TestClient(_app()).post(path, json={})

    assert response.status_code == 422, path
