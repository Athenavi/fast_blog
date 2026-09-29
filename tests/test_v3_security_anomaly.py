"""测试：异常行为检测（真实表窗口聚合 + 可持久化阈值）

不需要数据库：

  - ``_severity`` / ``_ip_weight`` 是纯函数
  - 阈值的默认值与合法键集合是纯数据
  - ``save_thresholds`` 对未知键 / 空更新**在触碰 db 之前**就拒绝
  - 端点注册与鉴权分流

真实检测（``login_attempts`` + ``audit_logs`` 聚合）走运行时验证。
"""

import pytest
from fastapi import FastAPI

from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.system.security.anomaly_service import (
    DEFAULT_THRESHOLDS,
    THRESHOLD_KEYS,
    anomaly_detection_service,
    _ip_weight,
    _severity,
)

ANOMALIES_PATH = "/api/v3/system/security/anomalies"
THRESHOLDS_PATH = "/api/v3/system/security/anomalies/thresholds"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 纯函数
@pytest.mark.parametrize(
    ("count", "threshold", "expected"),
    [
        (5, 5, "medium"),
        (9, 5, "medium"),
        (10, 5, "high"),
        (14, 5, "high"),
        (15, 5, "critical"),
        (100, 5, "critical"),
    ],
)
def test_severity_scales_with_multiple(count, threshold, expected):
    assert _severity(count, threshold) == expected


def test_severity_handles_non_positive_threshold():
    assert _severity(3, 0) == "medium"


def test_ip_weight_prefers_credential_spray():
    brute = {"type": "brute_force", "count": 10}
    spray = {"type": "credential_spray", "count": 10}
    rate = {"type": "rate_abuse", "count": 100}
    other = {"type": "unusual_hours", "count": 10}

    assert _ip_weight(spray) > _ip_weight(brute) > _ip_weight(other)
    assert _ip_weight(rate) == 10


# ------------------------------------------------------------------ 阈值元数据
def test_default_thresholds_cover_expected_keys():
    for key in (
            "brute_force_failures",
            "brute_force_window_minutes",
            "spray_usernames",
            "spray_window_minutes",
            "unusual_hour_start",
            "unusual_hour_end",
            "unusual_hour_logins",
            "rate_abuse_actions",
            "rate_abuse_window_minutes",
            "max_items",
    ):
        assert key in DEFAULT_THRESHOLDS
        assert key in THRESHOLD_KEYS


def test_default_thresholds_are_positive_ints():
    assert all(isinstance(v, int) and v >= 0 for v in DEFAULT_THRESHOLDS.values())


# ------------------------------------------------------------------ 阈值写入校验（不触库）
@pytest.mark.asyncio
async def test_save_thresholds_rejects_unknown_key():
    with pytest.raises(BadRequestError):
        await anomaly_detection_service.save_thresholds(None, {"not_a_threshold": 1})  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_save_thresholds_rejects_empty_payload():
    with pytest.raises(BadRequestError):
        await anomaly_detection_service.save_thresholds(None, {})  # type: ignore[arg-type]

# ------------------------------------------------------------------ 端点
