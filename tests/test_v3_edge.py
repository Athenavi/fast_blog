"""_pending_test_edge.py —— 待迁入 ``tests/`` 的 **system/edge 纯函数**单测

本任务的环境**禁止写 ``tests/`` 目录、禁止执行 shell**，因此把 edge 模块的纯函数单测
临时放在模块目录内（文件名以下划线开头，不会被当作业务模块自动收集）。恢复后应移动到
``tests/test_v3_edge.py``。

只覆盖**不依赖 DB / 网络 / FastAPI** 的能力（全部逐行读自
``src/api/v3/modules/system/edge/service.py``）::

  - ``checksum``            SHA-256（长度 / 稳定性 / UTF-8 / ``None`` 当空串）
  - ``normalize_platform``  平台别名归一 + 未知平台抛 ``BadRequestError``
  - ``route_matches``       精确 / 前缀通配 ``*`` / 空值边界
  - ``find_route``          插入顺序取首个命中 / ``enabled`` 跳过 / 无命中
  - ``resolve_entry_code``  用户 code 原样优先，否则平台转发模板
  - ``_render_cloudflare_entry`` / ``_render_vercel_entry``  入口模板关键片段
  - ``build_artifact``      产物结构（入口名 / 文件清单 / 字节数 / SHA-256 / 总字节）
  - ``validate_code``       体积上限 / 禁用 API / 入口契约（违规 + 合规）
  - ``credential_status``   环境变量就绪（``delenv`` 后**如实**返回未配置）
  - ``EdgeFunctionService._summary`` / ``._detail`` / 模块级 ``_now_iso``

运行（在仓库根目录，确保可 ``import src.*``）::

    python -m pytest src/api/v3/modules/system/edge/_pending_test_edge.py -q

**本文件尚未运行**：本任务执行环境不允许跑 pytest，故仅静态编写；每条断言均来自
上表函数中被逐行读过的真实实现，未使用任何占位/猜测断言。
"""

import hashlib
from datetime import datetime

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.system.edge import service as edge_service
from src.api.v3.modules.system.edge.service import (
    PLATFORM_ALIASES,
    PLATFORM_CLOUDFLARE,
    PLATFORM_SPECS,
    PLATFORM_VERCEL,
    EdgeFunctionService,
    _now_iso,
    _render_cloudflare_entry,
    _render_vercel_entry,
    build_artifact,
    checksum,
    credential_status,
    find_route,
    normalize_platform,
    resolve_entry_code,
    route_matches,
    validate_code,
)


# =================================================================== checksum
def test_checksum_length_and_deterministic():
    h = checksum("hello world")
    # 同输入同输出（纯函数、无副作用）
    assert h == checksum("hello world")
    # SHA-256 十六进制摘要固定 64 字符
    assert len(h) == 64
    assert all(ch in "0123456789abcdef" for ch in h)


def test_checksum_matches_sha256_of_utf8():
    text = "边缘函数 edge"
    # 与标准库独立计算一致，且按 UTF-8 编码
    assert checksum(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert checksum("a") != checksum("b")


def test_checksum_none_treated_as_empty():
    # 实现为 ``(text or "").encode(...)``：None 与空串同值
    assert checksum(None) == checksum("")
    assert checksum(None) == hashlib.sha256(b"").hexdigest()


# ========================================================== normalize_platform
def test_normalize_platform_aliases():
    assert normalize_platform("Cloudflare") == PLATFORM_CLOUDFLARE
    assert normalize_platform("CF") == PLATFORM_CLOUDFLARE
    assert normalize_platform("  workers ") == PLATFORM_CLOUDFLARE
    assert normalize_platform("cloudflare_workers") == PLATFORM_CLOUDFLARE
    assert normalize_platform("Vercel") == PLATFORM_VERCEL
    assert normalize_platform("EDGE") == PLATFORM_VERCEL
    assert normalize_platform("vercel_edge") == PLATFORM_VERCEL
    # 别名表与标准名一致（防止今后拼写漂移）
    assert PLATFORM_ALIASES["cf"] == PLATFORM_CLOUDFLARE
    assert PLATFORM_ALIASES["edge"] == PLATFORM_VERCEL


def test_normalize_platform_unknown_raises():
    for bad in ("aws_lambda", "", None, "cloud"):
        with pytest.raises(BadRequestError):
            normalize_platform(bad)


# ============================================================= route_matches
def test_route_matches_exact_and_prefix():
    assert route_matches("/a", "/a") is True
    assert route_matches("/a", "/b") is False
    # 非通配的 pattern 只做精确匹配
    assert route_matches("/a", "/a/b") is False
    # 前缀通配：pattern 以 * 结尾
    assert route_matches("/api/*", "/api/x") is True
    assert route_matches("/api/*", "/api/") is True
    assert route_matches("/api/*", "/apid") is False


def test_route_matches_wildcards_and_edges():
    # 单独一个 * 匹配全部
    assert route_matches("*", "/anything") is True
    assert route_matches("*", "/") is True
    # * 去掉后即为前缀
    assert route_matches("/a*", "/a") is True
    assert route_matches("/a*", "/abc") is True
    assert route_matches("/a*", "/ba") is False
    # 空 pattern / None path → 不匹配
    assert route_matches("", "/a") is False
    assert route_matches(None, "/a") is False
    assert route_matches("/a", None) is False


# ================================================================ find_route
def test_find_route_returns_first_match_in_insertion_order():
    functions = {
        "first": {"route": "/api/*", "enabled": True},
        "second": {"route": "/api/x", "enabled": True},
    }
    # 两者都能匹配 /api/x；保持插入顺序，返回首个
    assert find_route(functions, "/api/x") == "first"


def test_find_route_skips_disabled():
    functions = {
        "off": {"route": "/api/*", "enabled": False},
        "on": {"route": "/api/x", "enabled": True},
    }
    assert find_route(functions, "/api/x") == "on"


def test_find_route_defaults_enabled_and_no_match():
    functions = {"a": {"route": "/only"}}
    # enabled 缺省时视为 True
    assert find_route(functions, "/only") == "a"
    assert find_route(functions, "/other") is None
    assert find_route({}, "/anything") is None


# ========================================================= resolve_entry_code
def test_resolve_entry_code_uses_custom_code_verbatim():
    # 提供了非空白 code → 原样返回（不 strip）
    assert resolve_entry_code(PLATFORM_CLOUDFLARE, {"code": "  x  "}) == "  x  "
    assert resolve_entry_code(PLATFORM_VERCEL, {"code": "export default 1"}) == "export default 1"
    # 纯空白 code 视为未提供 → 走平台模板
    rendered = resolve_entry_code(PLATFORM_VERCEL, {"code": "   ", "name": "g"})
    assert "Vercel Edge Function - g" in rendered


def test_resolve_entry_code_renders_platform_template(monkeypatch):
    # 冻结生成时间，使两次渲染（含 _now_iso）可比较
    monkeypatch.setattr(edge_service, "_now_iso", lambda: "2024-01-01T00:00:00")
    definition = {"name": "w", "route": "/x", "cache_ttl": 5}
    assert resolve_entry_code(PLATFORM_CLOUDFLARE, definition) == _render_cloudflare_entry(definition)
    assert resolve_entry_code(PLATFORM_VERCEL, definition) == _render_vercel_entry(definition)


# ======================================================= 入口模板关键片段
def test_render_cloudflare_entry_contains_route_and_fetch(monkeypatch):
    monkeypatch.setattr(edge_service, "_now_iso", lambda: "2024-01-01T00:00:00")
    code = _render_cloudflare_entry({"route": "/api/*", "cache_ttl": 60})
    assert "// Cloudflare Worker - 由 FastBlog 生成（system/edge）" in code
    assert "// 生成时间: 2024-01-01T00:00:00" in code
    assert 'const ROUTES = [{"route": "/api/*", "cache_ttl": 60}];' in code
    assert "export default {" in code
    assert "async fetch(request, env, ctx)" in code


def test_render_vercel_entry_contains_runtime_and_handler():
    code = _render_vercel_entry({"name": "greet", "cache_ttl": 30})
    assert "// Vercel Edge Function - greet" in code
    assert "export const config = { runtime: 'edge' };" in code
    assert "export default async function handler(request)" in code
    assert "const cacheTTL = 30;" in code
    assert "Edge Function: greet" in code


# ============================================================ build_artifact
def test_build_artifact_cloudflare_structure(monkeypatch):
    monkeypatch.setattr(edge_service, "_now_iso", lambda: "2024-01-01T00:00:00")
    definition = {"name": "myfn", "route": "/api/*", "cache_ttl": 60, "code": "export default {}"}
    artifact = build_artifact("cf", definition)  # 别名应被归一
    assert artifact["platform"] == PLATFORM_CLOUDFLARE
    assert artifact["label"] == "Cloudflare Workers"
    assert artifact["name"] == "myfn"
    assert artifact["route"] == "/api/*"
    assert artifact["cache_ttl"] == 60
    assert artifact["executed"] is False
    # 入口文件固定为 worker.js，且附带 wrangler.toml
    assert artifact["entry"] == "worker.js"
    assert [f["path"] for f in artifact["files"]] == ["worker.js", "wrangler.toml"]
    entry = artifact["files"][0]
    assert entry["role"] == "entry"
    assert entry["bytes"] == len("export default {}".encode("utf-8"))
    assert entry["sha256"] == checksum("export default {}")
    assert artifact["files"][1]["role"] == "config"
    # 汇总字段自洽
    assert artifact["entry_bytes"] == entry["bytes"]
    assert artifact["entry_sha256"] == entry["sha256"]
    assert artifact["total_bytes"] == sum(f["bytes"] for f in artifact["files"])


def test_build_artifact_vercel_entry_name_and_filelist():
    artifact = build_artifact("vercel", {"name": "greet", "code": "export default 1"})
    assert artifact["platform"] == PLATFORM_VERCEL
    assert artifact["label"] == "Vercel Edge"
    # vercel 的 entry_file 为 None → 用 "<name>.js"
    assert artifact["entry"] == "greet.js"
    assert [f["path"] for f in artifact["files"]] == ["greet.js", "vercel.json"]
    # 缺省 name 回落到 "edge"
    defaulted = build_artifact("vercel", {})
    assert defaulted["name"] == "edge"
    assert defaulted["entry"] == "edge.js"


def test_build_artifact_entry_matches_resolved_code(monkeypatch):
    monkeypatch.setattr(edge_service, "_now_iso", lambda: "2024-01-01T00:00:00")
    definition = {"name": "w", "route": "/x", "cache_ttl": 0}
    artifact = build_artifact(PLATFORM_CLOUDFLARE, definition)
    # 未提供 code 时，产物入口即平台模板渲染结果
    entry_code = resolve_entry_code(PLATFORM_CLOUDFLARE, definition)
    assert artifact["entry_sha256"] == checksum(entry_code)
    assert artifact["entry_bytes"] == len(entry_code.encode("utf-8"))


def test_build_artifact_unknown_platform_raises():
    with pytest.raises(BadRequestError):
        build_artifact("aws", {})


# ============================================================= validate_code
def test_validate_code_empty_errors():
    result = validate_code(PLATFORM_CLOUDFLARE, "")
    assert result["valid"] is False
    assert [e["rule"] for e in result["errors"]] == ["code-empty"]
    assert result["summary"] == {"errors": 1, "warnings": 0}
    # None 同样按空代码处理
    assert validate_code(PLATFORM_CLOUDFLARE, None)["valid"] is False


def test_validate_code_valid_cloudflare():
    code = "export default { async fetch(request) { return new Response('ok'); } };"
    result = validate_code(PLATFORM_CLOUDFLARE, code)
    assert result["platform"] == PLATFORM_CLOUDFLARE
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["byte_size"] == len(code.encode("utf-8"))
    assert result["size_limit"] == PLATFORM_SPECS[PLATFORM_CLOUDFLARE]["max_bytes"]


def test_validate_code_valid_vercel():
    code = (
        "export const config = { runtime: 'edge' };\n"
        "export default async function handler(request) { return new Response('ok'); }"
    )
    result = validate_code("vercel", code)
    assert result["platform"] == PLATFORM_VERCEL
    assert result["valid"] is True
    assert result["errors"] == []
    # 已声明 runtime → 无 runtime-config 警告
    assert result["warnings"] == []


def test_validate_code_cloudflare_entry_missing():
    result = validate_code(PLATFORM_CLOUDFLARE, "console.log('hi');")
    assert result["valid"] is False
    assert "entry-missing" in {e["rule"] for e in result["errors"]}


def test_validate_code_cloudflare_add_event_listener_entry():
    # addEventListener('fetch', ...) 也算合法入口契约
    code = "addEventListener('fetch', e => {});"
    result = validate_code(PLATFORM_CLOUDFLARE, code)
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_code_vercel_entry_missing_and_runtime_warning():
    result = validate_code(PLATFORM_VERCEL, "const x = 1;")
    assert result["valid"] is False
    assert "entry-missing" in {e["rule"] for e in result["errors"]}
    # 未声明 runtime → 建议性警告
    warning_rules = {w["rule"] for w in result["warnings"]}
    assert "runtime-config" in warning_rules


def test_validate_code_forbidden_error_rules():
    cases = {
        "eval": "export default {};\nconst x = eval('1');",
        "new-function": "export default {};\nconst f = new Function('return 1');",
        "require": "export default {};\nconst fs = require('fs');",
        "commonjs-exports": "export default {};\nmodule.exports = {};",
        "child-process": "export default {};\nimport cp from 'child_process';",
        "node-fs": "export default {};\nimport fs from 'fs';",
        "node-builtin": "export default {};\nimport os from 'node:os';",
    }
    for rule, code in cases.items():
        result = validate_code(PLATFORM_CLOUDFLARE, code)
        assert result["valid"] is False, rule
        assert rule in {e["rule"] for e in result["errors"]}, rule


def test_validate_code_warning_rules():
    cases = {
        "process-env": "export default {};\nconst t = process.env.TOKEN;",
        "browser-dom": "export default {};\nconst d = document.title;",
        "xhr": "export default {};\nconst x = new XMLHttpRequest();",
        "debugger": "export default {};\ndebugger;",
    }
    for rule, code in cases.items():
        result = validate_code(PLATFORM_CLOUDFLARE, code)
        assert rule in {w["rule"] for w in result["warnings"]}, rule
        # 只有 warning，不阻断
        assert result["valid"] is True, rule


def test_validate_code_size_limit_exceeded():
    limit = PLATFORM_SPECS[PLATFORM_CLOUDFLARE]["max_bytes"]
    code = "a" * (limit + 1)
    result = validate_code(PLATFORM_CLOUDFLARE, code)
    assert result["byte_size"] == len(code)
    assert result["size_limit"] == limit
    assert result["valid"] is False
    assert "size-limit" in {e["rule"] for e in result["errors"]}


def test_validate_code_size_warning_near_limit():
    limit = PLATFORM_SPECS[PLATFORM_CLOUDFLARE]["max_bytes"]
    # 超过 80% 但未超上限 → warning
    code = "a" * (int(limit * 0.8) + 1)
    result = validate_code(PLATFORM_CLOUDFLARE, code)
    assert result["byte_size"] > limit * 0.8
    assert result["byte_size"] <= limit
    assert "size-warning" in {w["rule"] for w in result["warnings"]}


def test_validate_code_checks_aggregates_buckets():
    result = validate_code(PLATFORM_CLOUDFLARE, "export default {};\ndebugger;")
    assert "debugger" in {c["rule"] for c in result["checks"]}
    assert len(result["checks"]) == len(result["errors"]) + len(result["warnings"])
    assert result["summary"] == {
        "errors": len(result["errors"]),
        "warnings": len(result["warnings"]),
    }


def test_validate_code_unknown_platform_raises():
    with pytest.raises(BadRequestError):
        validate_code("aws", "export default {}")


# ========================================================= credential_status
def test_credential_status_reports_not_configured_cloudflare(monkeypatch):
    # 清空相关环境变量后必须**如实**报未配置，不得伪造已配置
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    status = credential_status("cloudflare_workers")
    assert status["platform"] == PLATFORM_CLOUDFLARE
    assert status["available"] is False
    assert status["env"] == {"CLOUDFLARE_API_TOKEN": False, "CLOUDFLARE_ACCOUNT_ID": False}
    assert status["required_env"] == ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"]


def test_credential_status_reports_not_configured_vercel(monkeypatch):
    monkeypatch.delenv("VERCEL_TOKEN", raising=False)
    status = credential_status("vercel")
    assert status["platform"] == PLATFORM_VERCEL
    assert status["available"] is False
    assert status["env"] == {"VERCEL_TOKEN": False}
    assert status["required_env"] == ["VERCEL_TOKEN"]


def test_credential_status_available_when_env_set(monkeypatch):
    # 显式注入全部必需变量 → available 为 True（验证就绪分支）
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "t")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a")
    status = credential_status("cf")
    assert status["available"] is True
    assert status["env"] == {"CLOUDFLARE_API_TOKEN": True, "CLOUDFLARE_ACCOUNT_ID": True}


def test_credential_status_unknown_platform_raises():
    with pytest.raises(BadRequestError):
        credential_status("aws")


# =================================================== 服务视图 / 时间（纯逻辑）
def test_summary_strips_code_and_counts_bytes():
    definition = {"name": "x", "route": "/a", "code": "边缘", "enabled": True}
    summary = EdgeFunctionService._summary(definition)
    # code 本体被剔除，避免摘要泄露完整源码
    assert "code" not in summary
    assert summary["name"] == "x"
    assert summary["enabled"] is True
    assert summary["code_bytes"] == len("边缘".encode("utf-8"))
    assert summary["has_custom_code"] is True


def test_summary_without_code():
    assert EdgeFunctionService._summary({"name": "y"})["code_bytes"] == 0
    assert EdgeFunctionService._summary({"name": "y"})["has_custom_code"] is False
    none_code = EdgeFunctionService._summary({"name": "y", "code": None})
    assert none_code["code_bytes"] == 0
    assert none_code["has_custom_code"] is False
    blank = EdgeFunctionService._summary({"name": "y", "code": "   "})
    assert blank["code_bytes"] == 3
    assert blank["has_custom_code"] is False


def test_detail_returns_independent_copy():
    definition = {"name": "x", "code": "abc"}
    detail = EdgeFunctionService._detail(definition)
    assert detail == definition
    assert detail is not definition
    detail["name"] = "mutated"
    assert definition["name"] == "x"


def test_now_iso_seconds_precision():
    value = _now_iso()
    assert isinstance(value, str)
    parsed = datetime.fromisoformat(value)
    # timespec="seconds"：微秒为 0，长度固定 19（YYYY-MM-DDTHH:MM:SS）
    assert parsed.microsecond == 0
    assert len(value) == 19
