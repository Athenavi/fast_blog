# -*- coding: utf-8 -*-
"""阶段 0-2：MCP 真实可连接 + 权限对齐**真实三段权限码**。

修复前的三处硬伤（都能从这里看到对照）：

  1. **连不上**：`MCPServer.handle_request` 没有 `initialize`（标准客户端握手第一步就失败），
     也没有任何传输层（无 stdio、无 HTTP 端点）；
  2. **上下文恒为空**：全仓无人调用 `set_user_ctx` → 53 个工具全都返回"未登录"；
  3. **判权脱节**：`_perms.py` 用 `ROLE_HIERARCHY` 按 `user.role` 的**等级分**判权，
     而真实体系是 `module_{域}:{模块}:{动作}` 三段码 + 令牌 scopes 收窄。

本测试**不连数据库**：需要调用工具的地方把 handler 换成测试替身，
但**权限判定走的是真实映射表**（`TOOL_PERMISSIONS`）。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.mcp._context import UserCtx, get_user_ctx, set_user_ctx
from src.mcp.server import SUPPORTED_PROTOCOL_VERSIONS, mcp_server
from src.mcp.tools import _TOOL_DEFS
from src.mcp.tools._perms import (
    TOOL_PERMISSIONS,
    describe_tool_permissions,
    ensure_tool_allowed,
    has_permission,
)
from src.mcp.transport import handle_line

ARTICLE_VIEW = "module_content:article:view"
ARTICLE_CREATE = "module_content:article:create"
CATEGORY_VIEW = "module_content:category:view"


def _ctx(*codes, scopes=None, superuser=False) -> UserCtx:
    return UserCtx(
        id=1,
        username="tester",
        is_superuser=superuser,
        role="user",
        permission_codes=frozenset(codes),
        token_scopes=None if scopes is None else frozenset(scopes),
    )


@pytest.fixture(autouse=True)
def _clean_ctx():
    """每个用例后清空上下文，避免 contextvar 串味"""
    yield
    set_user_ctx(None)


@pytest.fixture
def stub_tool():
    """把指定工具的 handler 换成替身，用例结束还原（不触碰真实业务逻辑/数据库）"""
    swapped: list[tuple[str, object]] = []

    def _swap(name: str, result=None):
        original = mcp_server.tools[name]["handler"]
        mcp_server.tools[name]["handler"] = AsyncMock(return_value=result or {"ok": True})
        swapped.append((name, original))
        return mcp_server.tools[name]["handler"]

    yield _swap

    for name, original in swapped:
        mcp_server.tools[name]["handler"] = original


# ────────────────────────────────────────────────────── 1. 协议握手

@pytest.mark.asyncio
class TestHandshake:
    async def test_initialize_returns_capabilities(self):
        """修复前没有这个方法 → 标准 MCP 客户端会直接放弃连接"""
        resp = await mcp_server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "clientInfo": {"name": "cursor"}},
            }
        )
        result = resp["result"]
        assert result["protocolVersion"] == "2025-06-18"
        assert result["serverInfo"]["name"] == "fastapiadmin-mcp" or result["serverInfo"]["name"]
        assert set(result["capabilities"]) >= {"tools", "resources", "prompts"}

    async def test_initialize_negotiates_unknown_version(self):
        resp = await mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {"protocolVersion": "1.0-bogus"}}
        )
        assert resp["result"]["protocolVersion"] == SUPPORTED_PROTOCOL_VERSIONS[0]

    async def test_initialize_echoes_older_supported_version(self):
        resp = await mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}
        )
        assert resp["result"]["protocolVersion"] == "2024-11-05"

    async def test_ping(self):
        resp = await mcp_server.handle_request({"jsonrpc": "2.0", "id": 4, "method": "ping"})
        assert resp["result"] == {}

    async def test_notification_returns_none(self):
        """通知（无 id）按规范不回响应"""
        resp = await mcp_server.handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
        assert resp is None

    async def test_unknown_method_is_error(self):
        resp = await mcp_server.handle_request({"jsonrpc": "2.0", "id": 5, "method": "nope/whatever"})
        assert "error" in resp

    async def test_tools_list_exposes_required_permissions(self):
        resp = await mcp_server.handle_request({"jsonrpc": "2.0", "id": 6, "method": "tools/list"})
        tools = resp["result"]["tools"]
        assert tools, "至少应注册若干工具"
        by_name = {t["name"]: t for t in tools}
        meta = by_name["list_categories"]["_meta"]["requiredPermissions"]
        assert meta == [CATEGORY_VIEW]
        # 每个工具都必须带上权限信息（客户端可预判，而不是撞 403）
        assert all(t["_meta"]["requiredPermissions"] for t in tools)


# ────────────────────────────────────────────────────── 2. 权限判定（真实权限码）

class TestPermissionModel:
    def test_no_context_is_denied(self):
        set_user_ctx(None)
        assert has_permission(ARTICLE_VIEW) is False

    def test_requires_actual_code(self):
        set_user_ctx(_ctx(ARTICLE_VIEW))
        assert has_permission(ARTICLE_VIEW) is True
        assert has_permission(ARTICLE_CREATE) is False

    def test_any_semantics(self):
        set_user_ctx(_ctx(ARTICLE_VIEW))
        assert has_permission(ARTICLE_CREATE, ARTICLE_VIEW) is True

    def test_superuser_bypass(self):
        set_user_ctx(_ctx(superuser=True))
        assert has_permission(ARTICLE_CREATE) is True

    def test_wildcard_bypass(self):
        set_user_ctx(_ctx("*:*:*"))
        assert has_permission(ARTICLE_CREATE) is True

    def test_role_name_alone_grants_nothing(self):
        """这正是修复的要点：**角色名不再是权限**，只有权限码算数"""
        set_user_ctx(UserCtx(id=2, username="adm", is_superuser=False, role="admin"))
        assert has_permission(ARTICLE_CREATE) is False

    def test_token_scopes_narrow_the_user(self):
        """API Token 不能越权：实际生效 = 用户权限 ∩ 令牌 scopes"""
        ctx = _ctx(ARTICLE_VIEW, ARTICLE_CREATE, scopes=[ARTICLE_VIEW])
        assert ctx.effective_codes() == frozenset({ARTICLE_VIEW})
        set_user_ctx(ctx)
        assert has_permission(ARTICLE_VIEW) is True
        assert has_permission(ARTICLE_CREATE) is False

    def test_scope_cannot_widen(self):
        """令牌 scopes 里写了用户没有的码 → 依然拒绝（求交语义）"""
        ctx = _ctx(ARTICLE_VIEW, scopes=[ARTICLE_CREATE])
        assert ctx.effective_codes() == frozenset()
        set_user_ctx(ctx)
        assert has_permission(ARTICLE_CREATE) is False

    def test_every_registered_tool_declares_permissions(self):
        """防漏断言：注册了工具却没在 TOOL_PERMISSIONS 声明 → 运行期会被 fail-closed 拒绝，
        这里提前把它变成测试失败，避免上线后才发现。"""
        registered = {name for name, _desc, _params, _handler in _TOOL_DEFS}
        missing = sorted(registered - set(TOOL_PERMISSIONS))
        assert not missing, f"以下工具未声明权限码：{missing}"

    def test_every_declared_code_is_a_real_code(self):
        """声明的码必须是 codes.py 里真实存在的三段码（防止拼错导致永久拒绝）"""
        from src.api.v3.core.permission import codes as C

        real = {value for name, value in vars(C).items() if name.isupper() and isinstance(value, str)}
        unknown = {
            code
            for codes_tuple in TOOL_PERMISSIONS.values()
            for code in codes_tuple
            if code not in real
        }
        assert not unknown, f"以下权限码在 codes.py 中不存在：{sorted(unknown)}"


@pytest.mark.asyncio
class TestToolCallGuard:
    async def test_unauthenticated_call_denied(self, stub_tool):
        stub_tool("list_categories")
        set_user_ctx(None)
        resp = await mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "list_categories"}}
        )
        assert "error" in resp
        assert "未登录" in resp["error"]["message"]

    async def test_missing_permission_denied(self, stub_tool):
        handler = stub_tool("create_article")
        set_user_ctx(_ctx(ARTICLE_VIEW))  # 只有 view
        resp = await mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "create_article"}}
        )
        assert "error" in resp
        assert ARTICLE_CREATE in resp["error"]["message"]
        handler.assert_not_awaited(), "被拒时不得执行 handler"

    async def test_permitted_call_executes_handler(self, stub_tool):
        handler = stub_tool("list_categories", {"items": []})
        set_user_ctx(_ctx(CATEGORY_VIEW))
        resp = await mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "list_categories"}}
        )
        assert "result" in resp
        handler.assert_awaited_once()

    async def test_token_scope_narrows_tool_call(self, stub_tool):
        """令牌只有 view scope → 即便用户本身有 create 权限，工具也必须被拒"""
        handler = stub_tool("create_article")
        set_user_ctx(_ctx(ARTICLE_VIEW, ARTICLE_CREATE, scopes=[ARTICLE_VIEW]))
        resp = await mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "create_article"}}
        )
        assert "error" in resp
        handler.assert_not_awaited()

    async def test_undeclared_tool_is_fail_closed(self):
        """没有权限声明的工具（如临时注册的）一律拒绝，而不是默认放行"""
        mcp_server.register_tool("temporary_tool", "临时", {}, AsyncMock(return_value={}))
        try:
            set_user_ctx(_ctx(superuser=True))
            denial = ensure_tool_allowed("temporary_tool")
            assert denial is not None and denial["code"] == "FORBIDDEN"
        finally:
            mcp_server.tools.pop("temporary_tool", None)

    async def test_unknown_tool_reports_not_found(self):
        set_user_ctx(_ctx(CATEGORY_VIEW))
        resp = await mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "does_not_exist"}}
        )
        assert "Tool not found" in resp["error"]["message"]

    def test_describe_permissions_shape(self):
        described = describe_tool_permissions(["list_categories", "unknown_tool"])
        assert described["list_categories"] == [CATEGORY_VIEW]
        assert described["unknown_tool"] == []


# ────────────────────────────────────────────────────── 3. stdio 传输

@pytest.mark.asyncio
class TestStdioTransport:
    async def test_valid_request_returns_json(self):
        out = await handle_line('{"jsonrpc": "2.0", "id": 1, "method": "ping"}', None)
        assert out is not None and '"result"' in out

    async def test_bad_json_returns_parse_error(self):
        out = await handle_line("{not json", None)
        assert out is not None and "-32700" in out

    async def test_non_object_returns_invalid_request(self):
        out = await handle_line("[1, 2, 3]", None)
        assert out is not None and "-32600" in out

    async def test_notification_produces_no_output(self):
        out = await handle_line('{"jsonrpc": "2.0", "method": "notifications/initialized"}', None)
        assert out is None

    async def test_context_is_applied_and_cleared(self, stub_tool):
        """stdio 模式下传入的上下文对工具生效，且用完必须清空（不污染后续行）"""
        handler = stub_tool("list_categories", {"items": []})
        await handle_line(
            '{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_categories"}}',
            _ctx(CATEGORY_VIEW),
        )
        handler.assert_awaited_once()
        assert get_user_ctx() is None


# ────────────────────────────────────────────────────── 4. HTTP 端点

class TestHttpEndpoint:
    def test_router_exposes_single_post_endpoint(self):
        from src.mcp.http import router

        paths = [getattr(r, "path", None) for r in router.routes]
        assert "/mcp" in paths
        assert len(router.routes) == 1, "MCP 是单一端点，不应额外暴露路径"

    def test_endpoint_requires_authenticated_user(self):
        """端点必须挂认证依赖：未认证由 CurrentUser → 401，而不是匿名可用"""
        from src.mcp.http import router

        route = router.routes[0]
        dependant = getattr(route, "dependant", None)
        assert dependant is not None and dependant.dependencies, "缺少认证/DB 依赖"

    def test_scope_helper_reads_principal(self):
        from src.auth.api_token import Principal
        from src.mcp.http import _token_scopes

        request = MagicMock()
        request.state.principal = Principal(user=MagicMock(id=1), scopes=frozenset({CATEGORY_VIEW}), source="api_key")
        assert _token_scopes(request) == frozenset({CATEGORY_VIEW})

        request.state.principal = None
        assert _token_scopes(request) is None
