"""测试：维护模式（任务 14c）

不需要数据库：

  - ``evaluate`` 是**纯计算**（v2 的同名方法会顺手写配置文件，v3 不会）
  - ``parse_iso`` 容错
  - 白名单路径必须包含登录与健康探针（否则维护期间管理员进不去）
  - 端点注册与公开读 / 鉴权分流

真实拦截（中间件返回 503）与配置持久化走运行时验证。
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v3 import register_v3_routes
from src.api.v3.modules.system.maintenance.service import (
    ALLOWED_PATH_PREFIXES,
    CONFIG_KEY,
    DEFAULT_CONFIG,
    maintenance_service,
    parse_iso,
)

BASE = "/api/v3/system/maintenance"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 纯计算
def test_default_config_is_not_active():
    state = maintenance_service.evaluate(DEFAULT_CONFIG)

    assert state["active"] is False
    assert state["enabled"] is False
    assert state["in_schedule"] is False


def test_enabled_makes_it_active():
    state = maintenance_service.evaluate({**DEFAULT_CONFIG, "enabled": True})

    assert state["active"] is True


def test_whitelisted_ip_is_never_blocked():
    config = {**DEFAULT_CONFIG, "enabled": True, "whitelist_ips": ["10.0.0.1"]}

    assert maintenance_service.evaluate(config, client_ip="10.0.0.1")["active"] is False
    assert maintenance_service.evaluate(config, client_ip="10.0.0.2")["active"] is True


def test_schedule_window_activates_without_touching_config():
    now = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
    config = {
        **DEFAULT_CONFIG,
        "scheduled_start": (now - timedelta(hours=1)).isoformat(),
        "scheduled_end": (now + timedelta(hours=1)).isoformat(),
    }

    inside = maintenance_service.evaluate(config, now=now)
    assert inside["active"] is True and inside["in_schedule"] is True
    # 纯计算：配置对象本身不应被改写
    assert config["enabled"] is False
    assert DEFAULT_CONFIG["enabled"] is False


def test_schedule_window_expired_is_inactive():
    now = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
    config = {
        **DEFAULT_CONFIG,
        "scheduled_start": (now - timedelta(hours=3)).isoformat(),
        "scheduled_end": (now - timedelta(hours=2)).isoformat(),
    }

    assert maintenance_service.evaluate(config, now=now)["active"] is False


def test_message_and_retry_after_have_defaults():
    state = maintenance_service.evaluate(DEFAULT_CONFIG)

    assert state["message"]
    assert state["retry_after"] == 3600


# ------------------------------------------------------------------ 时间解析
@pytest.mark.parametrize(
    ("raw", "ok"),
    [
        ("2026-03-01T12:00:00Z", True),
        ("2026-03-01T12:00:00", True),
        ("2026-03-01T12:00:00+08:00", True),
        ("not-a-date", False),
        (None, False),
        ("", False),
    ],
)
def test_parse_iso(raw, ok):
    assert (parse_iso(raw) is not None) is ok


# ------------------------------------------------------------------ 白名单路径
def test_allowed_paths_cover_login_and_probes():
    joined = " ".join(ALLOWED_PATH_PREFIXES)

    assert "/api/v3/system/auth/login" in joined
    assert "/api/v3/health" in joined
    assert "/api/v3/system/maintenance" in joined


def test_config_key_constant():
    assert CONFIG_KEY == "maintenance.config"


# ------------------------------------------------------------------ 中间件
def test_middleware_importable_and_cache_invalidation():
    from src.middleware import maintenance_mode

    maintenance_mode.invalidate_cache()
    assert maintenance_mode.CACHE_TTL_SECONDS > 0
    assert hasattr(maintenance_mode, "MaintenanceModeMiddleware")


# ------------------------------------------------------------------ 端点


def test_status_is_public_and_writes_are_protected():
    client = TestClient(_app(), raise_server_exceptions=False)

    assert client.get(f"{BASE}/status").status_code not in (401, 403)
    assert client.get(f"{BASE}/config").status_code in (401, 403)
    assert client.post(f"{BASE}/enable", json={}).status_code in (401, 403)
    assert client.post(f"{BASE}/disable").status_code in (401, 403)
    assert client.put(f"{BASE}/message", json={"message": "x"}).status_code in (401, 403)
    assert client.post(f"{BASE}/schedule", json={"scheduled_start": "a", "scheduled_end": "b"}).status_code in (401,
                                                                                                                403)
    assert client.delete(f"{BASE}/whitelist/1.2.3.4").status_code in (401, 403)
