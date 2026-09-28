"""P6：站点健康检查接线

背景：``shared/services/system/site_health.py`` 一直零引用，且它的「数据库连接」检查是
**占位实现**（定义了探测协程却从未调用，永远返回「正常」）。本批把它改造为真实执行
``SELECT 1``，并接到 ``GET /api/v3/system/health/site-report``（需登录 + monitor:view）。

覆盖：
  1. 五组检查齐全、总分与状态合理
  2. 数据库探测真的反映成功 / 失败
  3. SECRET_KEY 弱值（未设置 / 占位值 / 过短）被判 fail
  4. 路由已注册且需要鉴权
"""

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.services.system.site_health import SiteHealthService
from src.api.v3 import register_v3_routes


class _OkSession:
    """只支持 ``execute`` 的假会话（模拟可用数据库）"""

    async def execute(self, *_args, **_kwargs):
        return None


class _BrokenSession:
    async def execute(self, *_args, **_kwargs):
        raise RuntimeError("connection refused")


def test_run_full_check_has_five_groups():
    data = asyncio.run(SiteHealthService().run_full_check(_OkSession()))

    assert set(data["checks"]) == {"system", "database", "storage", "security", "performance"}
    assert 0 <= data["overall_score"] <= 100
    assert data["status"] in {"good", "warning", "critical"}
    assert data["timestamp"]


def test_database_check_reports_success_and_failure():
    svc = SiteHealthService()

    ok_rows = asyncio.run(svc.check_database(_OkSession()))
    ok = next(row for row in ok_rows if row["name"] == "数据库连接")
    assert ok["status"] == "pass" and ok["score"] == 1.0

    bad_rows = asyncio.run(svc.check_database(_BrokenSession()))
    bad = next(row for row in bad_rows if row["name"] == "数据库连接")
    assert bad["status"] == "fail" and bad["score"] == 0.0
    assert "connection refused" in bad["error"]


def test_weak_secret_key_is_flagged(monkeypatch):
    svc = SiteHealthService()

    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing-only")
    weak = next(row for row in svc.check_security() if row["name"] == "SECRET_KEY")
    assert weak["status"] == "fail"
    assert weak["recommendation"]

    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    strong = next(row for row in svc.check_security() if row["name"] == "SECRET_KEY")
    assert strong["status"] == "pass"
    assert strong["recommendation"] is None


def test_report_text_format_mentions_score():
    report = asyncio.run(SiteHealthService().generate_report("text", _OkSession()))
    assert "站点健康检查报告" in report
    assert "总体评分" in report


def test_site_report_route_registered_and_guarded():
    app = FastAPI()
    register_v3_routes(app)
    assert "/api/v3/system/health/site-report" in {route.path for route in app.routes}

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/api/v3/system/health/site-report").status_code == 401
