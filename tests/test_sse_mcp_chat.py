# -*- coding: utf-8 -*-
"""
AI Chat SSE 端点集成测试。

覆盖范围：
  - /api/v2/mcp/chat/stream — SSE 流式聊天
    ✓ 正常 token 流
    ✓ 工具调用 + 工具结果事件
    ✓ LLM 错误时的 SSE error 事件
    ✓ 自定义 conversation_id 传递
  - /api/v2/mcp/tools — MCP 工具列表
  - /api/v2/mcp/info — 服务器信息

WHY these tests exist:
  SSE 端点是 AI Chat 的前端直连接口。如果它出问题，整个 AI Chat 功能不可用。
  这些测试确保端点按预期响应 SSE 事件格式，且不因重构而破坏。
"""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from src.api.v2.mcp import router as mcp_router

pytestmark = pytest.mark.asyncio

# ============================================================================
# Test app setup
# ============================================================================

@pytest.fixture
def app():
    """Test FastAPI app with MCP router and mocked auth."""
    application = FastAPI()
    application.include_router(mcp_router)

    # Override jwt_required to bypass authentication
    async def _mock_current_user():
        return type("User", (), {"id": 1, "username": "test-user"})()

    from src.auth.auth_deps import jwt_required_dependency
    application.dependency_overrides[jwt_required_dependency] = _mock_current_user

    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """httpx AsyncClient wired to the test app (ASGI, no network)."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# ============================================================================
# SSE streaming chat — events
# ============================================================================

class TestChatStreamSSE:
    """SSE streaming chat endpoint — event content and ordering."""

    STREAM_URL = "/mcp/chat/stream"

    def _request_body(self, **overrides) -> dict:
        """Default chat request payload."""
        body = {
            "endpoint": "https://fake-llm.example.com",
            "api_key": "sk-test",
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 1024,
            "temperature": 0.7,
        }
        body.update(overrides)
        return body

    @patch("src.api.v2.mcp.stream_agent")
    async def test_streams_text_token(self, mock_stream, client):
        """Text-only response: yields token events."""
        async def _gen():
            yield {"type": "token", "content": "Hello! "}
            yield {"type": "token", "content": "How can I help?"}
            yield {"type": "done", "content": "Hello! How can I help?"}

        mock_stream.return_value = _gen()

        async with client as ac:
            resp = await ac.post(self.STREAM_URL, json=self._request_body())

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["cache-control"] == "no-cache"

        body = resp.text
        events = [line for line in body.strip().split("\n") if line.startswith("data: ")]

        assert len(events) == 3
        assert json.loads(events[0][6:]) == {"type": "token", "content": "Hello! "}
        assert json.loads(events[1][6:]) == {"type": "token", "content": "How can I help?"}
        assert json.loads(events[2][6:])["type"] == "done"

    @patch("src.api.v2.mcp.stream_agent")
    async def test_streams_tool_call_events(self, mock_stream, client):
        """Tool call response: yields tool_call + tool_result events."""
        async def _gen():
            yield {"type": "token", "content": "Let me search..."}
            yield {"type": "tool_call", "name": "create_article", "args": {"title": "AI"}}
            yield {"type": "tool_result", "name": "create_article", "content": '{"success": true}'}
            yield {"type": "done", "content": "Article created."}

        mock_stream.return_value = _gen()

        async with client as ac:
            resp = await ac.post(self.STREAM_URL, json=self._request_body())

        assert resp.status_code == 200
        lines = [l for l in resp.text.split("\n") if l.startswith("data: ")]
        assert len(lines) == 4

        event2 = json.loads(lines[1][6:])
        assert event2["type"] == "tool_call"
        assert event2["name"] == "create_article"
        assert event2["args"] == {"title": "AI"}

        event3 = json.loads(lines[2][6:])
        assert event3["type"] == "tool_result"
        assert event3["name"] == "create_article"

    @patch("src.api.v2.mcp.stream_agent")
    async def test_llm_error_yields_sse_error_event(self, mock_stream, client):
        """LLM call failure yields SSE error event (not HTTP 500)."""
        async def _gen():
            yield {"type": "error", "message": "Rate limit exceeded"}

        mock_stream.return_value = _gen()

        async with client as ac:
            resp = await ac.post(self.STREAM_URL, json=self._request_body())

        assert resp.status_code == 200  # SSE 端点永远 200
        lines = [l for l in resp.text.split("\n") if l.startswith("data: ")]
        assert len(lines) >= 1
        event = json.loads(lines[0][6:])
        assert event["type"] == "error"
        assert "Rate limit" in event["message"]

    @patch("src.api.v2.mcp.stream_agent")
    async def test_passes_custom_conversation_id(self, mock_stream, client):
        """Custom conversation_id is forwarded to stream_agent."""
        async def _gen():
            yield {"type": "done", "content": "OK"}

        mock_stream.return_value = _gen()

        async with client as ac:
            resp = await ac.post(
                self.STREAM_URL,
                json=self._request_body(conversation_id="my-custom-id"),
            )

        assert resp.status_code == 200

        # Verify conversation_id was passed to stream_agent
        call_args = mock_stream.call_args
        assert call_args is not None
        # stream_agent(cfg, messages, conversation_id=conv_id)
        kwargs = call_args[1]
        assert kwargs.get("conversation_id") == "my-custom-id"

    @patch("src.api.v2.mcp.stream_agent")
    async def test_response_headers_for_sse(self, mock_stream, client):
        """SSE response has correct headers for streaming."""
        async def _gen():
            yield {"type": "done", "content": "OK"}

        mock_stream.return_value = _gen()

        async with client as ac:
            resp = await ac.post(self.STREAM_URL, json=self._request_body())

        assert resp.headers.get("x-accel-buffering") == "no"
        assert resp.headers.get("connection") == "keep-alive"

    async def test_requires_authentication(self, client, app):
        """Without valid JWT, endpoint returns 401/403."""
        # Remove the dependency override to test auth
        from src.auth.auth_deps import jwt_required_dependency
        app.dependency_overrides.pop(jwt_required_dependency, None)

        async with client as ac:
            resp = await ac.post(self.STREAM_URL, json=self._request_body())

        assert resp.status_code in (401, 403)


# ============================================================================
# Non-streaming chat
# ============================================================================

class TestChatNonStream:
    """Non-streaming chat endpoint."""

    URL = "/mcp/chat"

    def _body(self, **kw):
        body = {
            "endpoint": "https://fake-llm.example.com",
            "api_key": "sk-test",
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hi"}],
        }
        body.update(kw)
        return body

    @patch("src.api.v2.mcp.run_agent")
    async def test_successful_response(self, mock_run, client):
        """Returns ApiResponse with assistant content."""
        state = AsyncMock()
        state.errors = []
        state.messages = [{"role": "assistant", "content": "Hello!"}]
        mock_run.return_value = state

        async with client as ac:
            resp = await ac.post(self.URL, json=self._body())

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["content"] == "Hello!"
        assert "conversation_id" in data["data"]

    @patch("src.api.v2.mcp.run_agent")
    async def test_error_returns_error_field(self, mock_run, client):
        """LLM error returns success=False with error message."""
        state = AsyncMock()
        state.errors = ["API key invalid"]
        state.messages = []
        mock_run.return_value = state

        async with client as ac:
            resp = await ac.post(self.URL, json=self._body())

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "API key invalid"


# ============================================================================
# Tools & Info
# ============================================================================

class TestToolsEndpoint:
    """MCP tools listing."""

    @patch("src.api.v2.mcp.mcp_server")
    async def test_returns_tool_list(self, mock_server, client):
        """Returns tools in ApiResponse format."""
        mock_server.get_openai_tools.return_value = [
            {"type": "function", "function": {"name": "create_article"}},
        ]

        async with client as ac:
            resp = await ac.get("/mcp/tools")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["function"]["name"] == "create_article"


class TestInfoEndpoint:
    """MCP server info."""

    @patch("src.api.v2.mcp.mcp_server")
    async def test_returns_server_info(self, mock_server, client):
        """Returns server info in ApiResponse format."""
        mock_server.get_server_info.return_value = {
            "name": "fastblog-mcp",
            "version": "1.0.0",
            "tools_count": 8,
        }

        async with client as ac:
            resp = await ac.get("/mcp/info")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["name"] == "fastblog-mcp"
        assert data["data"]["backend"] == "mcp.agent"
