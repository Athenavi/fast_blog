"""测试：多站点（域名解析 + 用户归属）

不需要数据库：

  - ``normalize_domain`` / ``split_domains`` / ``join_domains`` 是纯函数
    （存储格式与 v3 既有约定一致：JSON 数组，同时兼容逗号分隔的历史文本）
  - 新增端点注册与鉴权分流（``/resolve`` 公开，其余需 ``site:*``）

真实解析（sites 表按 Host 匹配、成员增删）走运行时验证。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v3 import register_v3_routes
from src.api.v3.modules.system.site.multisite_service import (
    join_domains,
    normalize_domain,
    split_domains,
)

BASE = "/api/v3/system/site"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 纯函数
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Blog.Example.COM", "blog.example.com"),
        ("https://blog.example.com/path?x=1", "blog.example.com"),
        ("blog.example.com:8080", "blog.example.com"),
        ("*.example.com", "example.com"),
        ("  ", ""),
        (None, ""),
    ],
)
def test_normalize_domain(raw, expected):
    assert normalize_domain(raw) == expected


def test_split_domains_reads_json_array():
    assert split_domains('["a.example.com", "b.example.com"]') == ["a.example.com", "b.example.com"]


def test_split_domains_tolerates_legacy_text():
    assert split_domains("a.example.com, b.example.com;c.example.com") == [
        "a.example.com",
        "b.example.com",
        "c.example.com",
    ]


def test_split_domains_deduplicates_and_normalizes():
    assert split_domains("Blog.example.com, https://blog.example.com") == ["blog.example.com"]


def test_split_domains_handles_empty_and_broken_json():
    assert split_domains(None) == []
    assert split_domains("") == []
    assert split_domains("[not-json") == ["not-json"]


def test_join_domains_roundtrips_with_split():
    domains = ["a.example.com", "b.example.com"]

    assert split_domains(join_domains(domains)) == domains


# ------------------------------------------------------------------ 端点


def test_resolve_requires_domain_param():
    """公开端点：缺 domain 参数应 422（而不是 401）"""
    assert TestClient(_app()).get(f"{BASE}/resolve").status_code == 422
