"""测试：屏幕选项（只测纯函数与校验逻辑）

不需要数据库。只覆盖 ``service.py`` 中与 DB 读写分离的纯函数：

  - ``validate_page`` / ``validate_option_key``：page 名与选项键的校验
  - ``normalize_options``：options 归一化与体积 / 可序列化校验
  - ``merge_default_options``：默认值合并
  - ``ScreenOptionsService.storage_key``：每用户存储键

**不测** ``register_v3_routes`` 的路由注册（本模块尚未登记进 ``DOMAIN_MODULES``，
注册面由启动期用例统一覆盖）。真实落库（``system_settings`` 的
``screen_options.{user_id}``）走运行时验证。
"""

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.system.screen_options.service import (
    DEFAULT_OPTIONS,
    MAX_OPTION_KEY_LEN,
    MAX_OPTIONS_PER_PAGE,
    MAX_PAGE_LEN,
    MAX_VALUE_BYTES,
    ScreenOptionsService,
    merge_default_options,
    normalize_options,
    screen_options_service,
    validate_option_key,
    validate_page,
)


# ------------------------------------------------------------------ page 校验
@pytest.mark.parametrize(
    "page", ["articles", "users", "media", "content.article", "user-profile", "sys_cache"]
)
def test_validate_page_accepts_common_names(page):
    assert validate_page(page) == page


def test_validate_page_strips_surrounding_whitespace():
    assert validate_page("  articles  ") == "articles"


def test_validate_page_accepts_exactly_max_length():
    page = "x" * MAX_PAGE_LEN
    assert validate_page(page) == page


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "a/b", "a b", "文章", None, 123, "x" * (MAX_PAGE_LEN + 1)],
)
def test_validate_page_rejects_bad_names(bad):
    with pytest.raises(BadRequestError):
        validate_page(bad)


# ------------------------------------------------------------------ 选项键校验
def test_validate_option_key_normalizes_whitespace():
    assert validate_option_key("  per_page  ") == "per_page"


@pytest.mark.parametrize("bad", ["", "   ", None, 5, "k" * (MAX_OPTION_KEY_LEN + 1)])
def test_validate_option_key_rejects_bad(bad):
    with pytest.raises(BadRequestError):
        validate_option_key(bad)


# ------------------------------------------------------------------ options 归一化
def test_normalize_options_none_and_empty():
    assert normalize_options(None) == {}
    assert normalize_options({}) == {}


def test_normalize_options_keeps_values_and_normalizes_keys():
    result = normalize_options(
        {" per_page ": 50, "columns": ["title"], "order": "asc", "pinned": None}
    )
    assert result == {"per_page": 50, "columns": ["title"], "order": "asc", "pinned": None}


def test_normalize_options_returns_fresh_dict():
    source = {"per_page": 50}
    result = normalize_options(source)
    assert result is not source
    result["order"] = "asc"
    assert "order" not in source


@pytest.mark.parametrize("bad", [[1, 2, 3], "per_page", 5, True])
def test_normalize_options_rejects_non_dict(bad):
    with pytest.raises(BadRequestError):
        normalize_options(bad)


def test_normalize_options_accepts_exactly_max_keys():
    payload = {f"k{i}": i for i in range(MAX_OPTIONS_PER_PAGE)}
    assert len(normalize_options(payload)) == MAX_OPTIONS_PER_PAGE


def test_normalize_options_rejects_too_many_keys():
    payload = {f"k{i}": i for i in range(MAX_OPTIONS_PER_PAGE + 1)}
    with pytest.raises(BadRequestError):
        normalize_options(payload)


def test_normalize_options_rejects_unserializable_value():
    with pytest.raises(BadRequestError):
        normalize_options({"weird": {1, 2, 3}})  # set 不可 JSON 序列化


def test_normalize_options_rejects_nan():
    with pytest.raises(BadRequestError):
        normalize_options({"n": float("nan")})


def test_normalize_options_rejects_oversized_value():
    with pytest.raises(BadRequestError):
        normalize_options({"blob": "x" * (MAX_VALUE_BYTES + 1)})


def test_normalize_options_rejects_oversized_page():
    # 每个值都在单值上限内，但整页合计超过页面上限
    payload = {f"k{i}": "x" * 6000 for i in range(3)}
    with pytest.raises(BadRequestError):
        normalize_options(payload)


# ------------------------------------------------------------------ 默认值合并
def test_merge_default_options_without_input_returns_defaults():
    assert merge_default_options() == DEFAULT_OPTIONS


def test_merge_default_options_overrides_and_keeps_extras():
    merged = merge_default_options({"per_page": 5, "custom": True})

    assert merged["per_page"] == 5
    assert merged["custom"] is True
    assert merged["order_by"] is None
    assert merged["columns"] == []


def test_merge_default_options_does_not_share_default_list():
    merged = merge_default_options()
    merged["columns"].append("title")

    assert DEFAULT_OPTIONS["columns"] == []


# ------------------------------------------------------------------ 存储键
def test_storage_key_is_scoped_per_user():
    assert screen_options_service.storage_key(7) == "screen_options.7"
    assert ScreenOptionsService.storage_key(0) == "screen_options.0"
