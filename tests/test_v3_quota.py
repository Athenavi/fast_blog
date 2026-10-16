"""测试：站点配额（只测纯函数与校验，不连数据库）

覆盖：

  1. 默认配额（四项资源）与不限配额（``0`` / ``null``）的处理
  2. ``remaining`` / ``usage_percent`` / ``exceeded`` 的计算
  3. 配额更新的校验（未知键 / 负值 / 非整数 / 布尔被拒）
  4. ``check_resource`` 的放行 / 拒绝 / 边界 / 未知用量不拦
  5. ``parse_settings`` / ``resolve_quota`` 的解析与合并

**不测** ``register_v3_routes`` 的路由注册——本模块尚未登记进 ``DOMAIN_MODULES``，
真实持久化与端点行为走运行时（PostgreSQL）验证。
"""

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.system.quota.service import (
    DEFAULT_QUOTA,
    QUOTA_SETTINGS_KEY,
    RESOURCE_TYPES,
    check_resource,
    ensure_resource_type,
    is_unlimited,
    parse_settings,
    quota_percent,
    quota_remaining,
    resolve_quota,
    summarize,
    validate_quota_update,
)


def _quota(**overrides):
    """在默认配额上覆盖若干项"""
    return {**DEFAULT_QUOTA, **overrides}


# ------------------------------------------------------------------ 默认配额 / 不限
def test_default_quota_covers_four_resources():
    assert set(DEFAULT_QUOTA) == {"articles", "media", "users", "storage_mb"}
    assert RESOURCE_TYPES == ("articles", "media", "users", "storage_mb")


def test_quota_settings_key_constant():
    assert QUOTA_SETTINGS_KEY == "quota"


@pytest.mark.parametrize(
    ("limit", "expected"), [(None, True), (0, True), (1, False), (5120, False)]
)
def test_is_unlimited(limit, expected):
    assert is_unlimited(limit) is expected


# ------------------------------------------------------------------ remaining / percent
def test_quota_percent_basic():
    assert quota_percent(50, 100) == 50.0
    assert quota_percent(0, 100) == 0.0
    assert quota_percent(1, 3) == 33.33


def test_quota_percent_none_for_unlimited_or_unknown():
    assert quota_percent(10, 0) is None
    assert quota_percent(10, None) is None
    assert quota_percent(None, 100) is None


def test_quota_remaining_basic():
    assert quota_remaining(30, 100) == 70
    assert quota_remaining(100, 100) == 0
    assert quota_remaining(150, 100) == 0  # 剩余量不为负


def test_quota_remaining_none_when_unlimited_or_unknown():
    assert quota_remaining(5, 0) is None
    assert quota_remaining(5, None) is None
    assert quota_remaining(None, 100) is None


def test_summarize_reports_exceeded_and_shapes():
    quota = {"articles": 10, "media": 5, "users": 0, "storage_mb": 100}
    usage = {"articles": 10, "media": 2, "users": 3, "storage_mb": 150}

    summary = summarize(quota, usage)

    assert set(summary) == {"remaining", "usage_percent", "exceeded"}
    # articles 达到上限、storage_mb 超过上限都算 exceeded；users 不限故不算
    assert sorted(summary["exceeded"]) == ["articles", "storage_mb"]
    assert summary["remaining"]["media"] == 3
    assert summary["remaining"]["users"] is None
    assert summary["usage_percent"]["articles"] == 100.0
    assert summary["usage_percent"]["users"] is None


def test_summarize_treats_none_usage_as_unknown_not_exceeded():
    usage = {"articles": None, "media": None, "users": 1, "storage_mb": None}

    summary = summarize(DEFAULT_QUOTA, usage)

    assert "articles" not in summary["exceeded"]
    assert summary["remaining"]["articles"] is None
    assert summary["usage_percent"]["articles"] is None
    assert summary["usage_percent"]["users"] == round(1 / DEFAULT_QUOTA["users"] * 100, 2)


# ------------------------------------------------------------------ 解析 / 合并
def test_parse_settings_variants():
    assert parse_settings(None) == {}
    assert parse_settings("") == {}
    assert parse_settings("   ") == {}
    assert parse_settings("{bad json") == {}
    assert parse_settings("[1, 2, 3]") == {}
    assert parse_settings('{"quota": {"articles": 7}}') == {"quota": {"articles": 7}}
    assert parse_settings({"quota": {"articles": 7}}) == {"quota": {"articles": 7}}


def test_resolve_quota_merges_defaults():
    quota = resolve_quota({"quota": {"articles": 3}})

    assert quota["articles"] == 3
    assert quota["media"] == DEFAULT_QUOTA["media"]
    assert quota["users"] == DEFAULT_QUOTA["users"]
    assert quota["storage_mb"] == DEFAULT_QUOTA["storage_mb"]


def test_resolve_quota_ignores_unknown_and_invalid():
    quota = resolve_quota(
        {"quota": {"articles": -1, "bogus": 5, "media": None, "users": 12}}
    )

    assert quota["articles"] == DEFAULT_QUOTA["articles"]  # 负数被忽略 → 回退默认
    assert "bogus" not in quota
    assert quota["media"] is None  # null 表示不限
    assert quota["users"] == 12


def test_resolve_quota_without_key_uses_defaults():
    assert resolve_quota({}) == DEFAULT_QUOTA
    assert resolve_quota(None) == DEFAULT_QUOTA


# ------------------------------------------------------------------ 资源类型 / 更新校验
def test_ensure_resource_type_accepts_known():
    assert ensure_resource_type("users") == "users"


def test_ensure_resource_type_rejects_unknown():
    with pytest.raises(BadRequestError):
        ensure_resource_type("widgets")


def test_validate_quota_update_accepts_non_negative_and_none():
    clean = validate_quota_update({"articles": 0, "media": None, "users": 10})

    assert clean == {"articles": 0, "media": None, "users": 10}


@pytest.mark.parametrize(
    "bad",
    [
        {"articles": -1},
        {"widgets": 5},
        {"users": "10"},
        {"media": 1.5},
        {"articles": True},
    ],
)
def test_validate_quota_update_rejects_bad_input(bad):
    with pytest.raises(BadRequestError):
        validate_quota_update(bad)


def test_validate_quota_update_rejects_non_dict():
    with pytest.raises(BadRequestError):
        validate_quota_update(["articles"])


# ------------------------------------------------------------------ check_resource
def test_check_resource_allowed_within_limit():
    result = check_resource("articles", 100, _quota(articles=1000), {"articles": 100})

    assert result["allowed"] is True
    assert result["current"] == 100
    assert result["limit"] == 1000
    assert result["remaining"] == 900


def test_check_resource_denied_over_limit():
    result = check_resource("articles", 50, _quota(articles=100), {"articles": 80})

    assert result["allowed"] is False
    assert result["remaining"] == 20
    assert "不足" in result["reason"]


def test_check_resource_boundary_exact_fit():
    result = check_resource("users", 20, _quota(users=100), {"users": 80})

    assert result["allowed"] is True
    assert result["remaining"] == 20


def test_check_resource_unlimited_always_allowed():
    result = check_resource("media", 999_999, _quota(media=0), {"media": 10})

    assert result["allowed"] is True
    assert result["limit"] is None
    assert result["remaining"] is None


def test_check_resource_unknown_usage_not_blocked():
    result = check_resource("articles", 1, _quota(articles=10), {"articles": None})

    assert result["allowed"] is True
    assert result["current"] is None
    assert result["remaining"] is None


def test_check_resource_rejects_unknown_type_and_bad_amount():
    with pytest.raises(BadRequestError):
        check_resource("widgets", 1, DEFAULT_QUOTA, {})
    with pytest.raises(BadRequestError):
        check_resource("articles", -1, DEFAULT_QUOTA, {})
    with pytest.raises(BadRequestError):
        check_resource("articles", 1.5, DEFAULT_QUOTA, {})
    with pytest.raises(BadRequestError):
        check_resource("articles", True, DEFAULT_QUOTA, {})
