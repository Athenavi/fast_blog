"""v3 路由契约（**唯一权威**）

本文件取代原先分散在 21 个 `test_v3_*.py` 里的「域模块清单 + 期望路径清单」副本
（`DOMAIN_MODULES` / `EXPECTED_PATHS` / `SYSTEM_MODULES` 等）。那些副本的问题是：
``src/api/v3/__init__.py`` 的 ``DOMAIN_MODULES`` 一旦变动，就要同步改 21 处，
漏一处只会让测试红、而不是让代码坏，维护成本远大于收益。

这里改用**派生 + 快照**两条更稳的检查：

1. **派生式**：登记完整性、未登记模块、路由冲突 / 遮蔽、统一响应形状、fail-fast ——
   全部从 ``DOMAIN_MODULES`` 与真实注册结果推导，新增模块时无需改测试。
2. **快照式**：``tests/v3_route_snapshot.txt`` 记录全部 ``METHOD /path``（882 条）。
   任何端点被删、改名、改了方法都会立刻失败——覆盖面比原先 21 份**部分**清单更全，
   而维护点只有 1 个文件（新增端点时跑
   ``python -m pytest tests/test_v3_route_contract.py --update-snapshot`` 更新）。

另附两条低维护的鉴权分流检查与 POST-only 方法检查（原分散在多个文件里的
``*_require_auth`` / ``test_get_on_post_routes_is_405`` 归口于此）。

本文件不连接数据库：鉴权检查在鉴权层即被拒，公开端点即使因无 DB 而 5xx 也算通过
（这里验证的是「是否需要登录」，不是「业务能否成功」）。
"""

import pathlib
import sys

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from src.api.v3 import DOMAIN_MODULES, register_v3_routes
from src.api.v3.core.discover import (
    RouteRegistrationError,
    assert_no_route_conflicts,
    find_route_conflicts,
    find_shadowed_routes,
    scan_unregistered_modules,
)

SNAPSHOT_PATH = pathlib.Path(__file__).with_name("v3_route_snapshot.txt")
UPDATE_SNAPSHOT = "--update-snapshot" in sys.argv


def _app(**kwargs) -> FastAPI:
    app = FastAPI()
    register_v3_routes(app, **kwargs)
    return app


def _routes(app: FastAPI) -> set[str]:
    """归一化成 ``METHOD /path`` 集合（忽略 HEAD/OPTIONS 自动方法）。"""
    out: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path or not path.startswith("/api/v3"):
            continue
        for method in getattr(route, "methods", set()) or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            out.add(f"{method} {path}")
    return out


# ---------------------------------------------------------------- 派生式：登记完整性
def test_registry_validates_and_has_no_unregistered_module():
    """所有模块都能导入、都已登记、无路由冲突与遮蔽（启动期 fail-fast 的真实断言）"""
    summary = register_v3_routes(FastAPI())

    assert summary["unregistered"] == [], f"磁盘上存在但未登记的模块：{summary['unregistered']}"
    assert summary["domains"].keys() == DOMAIN_MODULES.keys()


def test_every_registered_module_exposes_routes():
    """每个登记的模块至少要注册出一条路由（防止「目录建了、router 忘了写」）"""
    app = FastAPI()
    summary = register_v3_routes(app)
    paths = {getattr(route, "path", "") for route in app.routes}

    empty: list[str] = []
    for domain, modules in summary["domains"].items():
        for module in modules:
            prefix = f"/api/v3{domain}/"
            if not any(path.startswith(prefix) for path in paths):
                empty.append(f"{domain}/{module}")

    assert empty == [], f"这些模块没有注册出任何路由：{empty}"


def test_no_route_conflicts_or_shadowing():
    app = _app()
    assert find_route_conflicts(app.routes) == []
    assert find_shadowed_routes(app.routes) == []


# ---------------------------------------------------------------- 快照式：全量端点
def test_route_snapshot_is_up_to_date():
    """与 ``tests/v3_route_snapshot.txt`` 完全一致；端点增删改名都必须同步快照"""
    current = _routes(_app())
    if UPDATE_SNAPSHOT:
        SNAPSHOT_PATH.write_text("\n".join(sorted(current)) + "\n", encoding="utf-8", newline="\n")
        pytest.skip(f"快照已更新（{len(current)} 条）")

    expected = set(SNAPSHOT_PATH.read_text(encoding="utf-8").split("\n")) - {""}
    missing = sorted(expected - current)
    added = sorted(current - expected)

    assert not missing and not added, (
        "v3 路由与快照不一致。\n"
        f"  被删除/改名（快照里有、现在没有）：{missing}\n"
        f"  新增（现在有、快照里没有）：{added}\n"
        "确属有意变更时执行：python -m pytest tests/test_v3_route_contract.py --update-snapshot"
    )


# ---------------------------------------------------------------- 统一响应与 fail-fast
def test_unified_response_shape():
    """统一响应必须是 code / msg / data / pagination 四个字段"""
    resp = TestClient(_app()).get("/api/v3/system/health/live")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"code", "msg", "data", "pagination"}
    assert body["code"] == 200
    assert body["data"]["service"] == "fastblog-api-v3"


def test_fail_fast_on_missing_module(monkeypatch):
    """登记的模块不存在时必须抛错中止启动，而不是静默跳过"""
    monkeypatch.setitem(DOMAIN_MODULES, "/system", ("not_existed_module",))

    with pytest.raises(RouteRegistrationError) as exc_info:
        register_v3_routes(FastAPI())

    assert "not_existed_module" in str(exc_info.value)


def test_fail_fast_can_be_disabled(monkeypatch):
    monkeypatch.setitem(DOMAIN_MODULES, "/system", ("not_existed_module",))

    summary = register_v3_routes(FastAPI(), fail_fast=False)

    assert summary["domains"]["/system"] == []


def test_unregistered_module_is_reported(monkeypatch):
    monkeypatch.setitem(DOMAIN_MODULES, "/system", ())

    assert "/system/health" in register_v3_routes(FastAPI())["unregistered"]


def test_scan_unregistered_ignores_unknown_domain():
    assert scan_unregistered_modules("/not-a-domain", (), package="src.api.v3.modules") == []


# ---------------------------------------------------------------- 冲突检测本身
def test_route_conflict_is_detected():
    """同一 (方法, 路径) 注册两次必须被检出——含参数名不同的同路径"""
    router = APIRouter()

    @router.get("/articles/{article_id}")
    async def get_article(article_id: str):  # pragma: no cover - 仅注册用
        return {}

    @router.get("/articles/{article_id}")
    async def get_article_dup(article_id: str):  # pragma: no cover - 仅注册用
        return {}

    assert find_route_conflicts(router.routes)

    app = FastAPI()
    app.include_router(router)
    with pytest.raises(RouteRegistrationError):
        assert_no_route_conflicts(app, source="测试")


def test_route_conflict_detects_param_name_difference():
    router = APIRouter()

    @router.get("/user/{id}")
    async def by_id(id: int):  # pragma: no cover - 仅注册用
        return {}

    @router.get("/user/{uid}")
    async def by_uid(uid: int):  # pragma: no cover - 仅注册用
        return {}

    assert find_route_conflicts(router.routes)


def test_distinct_paths_do_not_conflict():
    assert find_route_conflicts(_app().routes) == []


# ---------------------------------------------------------------- 鉴权分流（与 DB 无关）
#: 明确**无需登录**的公开端点（匿名上报 / 公开读 / 静态生成）
PUBLIC_PATHS = (
    "/api/v3/system/health/live",
    "/api/v3/system/accessibility/css",
    "/api/v3/system/accessibility/skip-links",
    "/api/v3/system/webhook/events",
)
#: 明确**需要登录**的后台端点（鉴权层即拒，不会走到 DB）
PROTECTED_PATHS = (
    "/api/v3/system/user",
    "/api/v3/system/setting",
    "/api/v3/system/role",
    "/api/v3/system/log/audit",
    "/api/v3/content/article",
    "/api/v3/analytics/dashboard/overview",
    "/api/v3/ops/backup",
    "/api/v3/commerce/payment/gateway",
    "/api/v3/extension/plugin",
)


def test_public_endpoints_do_not_require_auth():
    """断言「不需要登录」：即便因无 DB 而 5xx 也算通过，401/403 才算违规"""
    client = TestClient(_app(), raise_server_exceptions=False)

    for path in PUBLIC_PATHS:
        resp = client.get(path)
        assert resp.status_code not in (401, 403), f"{path} 不应要求登录，实际 {resp.status_code}"


def test_admin_endpoints_require_auth_with_v3_error_shape():
    client = TestClient(_app(), raise_server_exceptions=False)

    for path in PROTECTED_PATHS:
        resp = client.get(path)
        assert resp.status_code == 401, f"{path} 应要求登录，实际 {resp.status_code}"
        assert resp.json()["code"] == 401


#: 明确**匿名可达**的 POST 端点（访客上报 / 支付回调 —— 不能被登录要求挡住）
ANONYMOUS_POST_PATHS = (
    "/api/v3/commerce/payment/callback/probe",
    "/api/v3/system/gdpr/consent",
    "/api/v3/analytics/tracking/page-view",
)


def test_anonymous_post_endpoints_are_not_blocked_by_auth():
    """断言「不要求登录」：无 token 时不应是 401/403（业务 400/422 属正常）"""
    client = TestClient(_app(), raise_server_exceptions=False)

    for path in ANONYMOUS_POST_PATHS:
        resp = client.post(path, json={})
        assert resp.status_code not in (401, 403), f"{path} 应允许匿名访问，实际 {resp.status_code}"


def test_post_only_routes_reject_get():
    """POST-only 路由用 GET 访问不应被当成合法入口"""
    client = TestClient(_app(), raise_server_exceptions=False)

    for path in (
            "/api/v3/ops/upgrade/check",
            "/api/v3/ops/upgrade/apply",
            "/api/v3/system/maintenance/enable",
            "/api/v3/content/article/preview-token/cleanup",
    ):
        assert client.get(path).status_code == 405, f"{path} 是 POST-only，GET 应 405"
