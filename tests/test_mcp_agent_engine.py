# -*- coding: utf-8 -*-
"""
MCP Agent Engine — unit tests for the core ReAct loop.

Covers:
  - LLMConfig / AgentState dataclasses
  - _msg_key, build_messages helpers
  - call_llm (mocked httpx)
  - execute_mcp_tool (mocked mcp_server)
  - get_tool_defs
  - run_agent (full loop: text-only, tool calls, error, max rounds)
  - stream_agent (async generator events)

WHY these tests exist:
  The agent engine is the brain of the AI Chat feature. Without tests,
  a regression in the ReAct loop silently breaks every downstream
  integration (MCP tools, chat SSE endpoint, sub-graph agents).
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.mcp.agent.engine import (
    LLMConfig,
    AgentState,
    _msg_key,
    build_messages,
    call_llm,
    execute_mcp_tool,
    get_tool_defs,
    run_agent,
    stream_agent,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cfg():
    """Minimal LLMConfig for tests."""
    return LLMConfig(
        endpoint="https://fake-llm.example.com",
        api_key="sk-test",
        model="gpt-4o-mini",
    )


@pytest.fixture
def sample_messages():
    """A short conversation history."""
    return [
        {"role": "user", "content": "Write a blog post about AI"},
    ]


@pytest.fixture
def text_only_response():
    """LLM response with no tool calls — just text."""
    return {
        "choices": [
            {
                "message": {
                    "content": "Here is a blog post about AI...",
                }
            }
        ]
    }


@pytest.fixture
def tool_call_response():
    """LLM response with one tool call."""
    return {
        "choices": [
            {
                "message": {
                    "content": "Let me create that article for you.",
                    "tool_calls": [
                        {
                            "id": "call_abc123",
                            "type": "function",
                            "function": {
                                "name": "create_article",
                                "arguments": json.dumps({
                                    "title": "AI in 2026",
                                    "content": "Content here",
                                    "status": "draft",
                                }),
                            },
                        }
                    ],
                }
            }
        ]
    }


@pytest.fixture
def two_tool_call_response():
    """LLM response with two sequential tool calls."""
    return {
        "choices": [
            {
                "message": {
                    "content": "Let me do both tasks.",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "create_article",
                                "arguments": json.dumps({"title": "T1", "content": "C1"}),
                            },
                        },
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {
                                "name": "get_system_stats",
                                "arguments": json.dumps({}),
                            },
                        },
                    ],
                }
            }
        ]
    }


# ============================================================================
# Dataclass tests
# ============================================================================

class TestLLMConfig:
    """LLMConfig dataclass construction."""

    def test_defaults(self):
        """Verify sensible defaults are applied."""
        c = LLMConfig(endpoint="http://test", api_key="k", model="m")
        assert c.endpoint == "http://test"
        assert c.api_key == "k"
        assert c.model == "m"
        assert c.system_prompt == "You are a helpful AI assistant."
        assert c.max_tokens == 4096
        assert c.temperature == 0.7
        assert c.max_tool_rounds == 10

    def test_custom_values(self):
        """Verify custom values override defaults."""
        c = LLMConfig(
            endpoint="http://test",
            api_key="k",
            model="m",
            system_prompt="Be concise.",
            max_tokens=1024,
            temperature=0.0,
            max_tool_rounds=3,
        )
        assert c.system_prompt == "Be concise."
        assert c.max_tokens == 1024
        assert c.temperature == 0.0
        assert c.max_tool_rounds == 3


class TestAgentState:
    """AgentState dataclass construction."""

    def test_defaults(self):
        """Verify defaults create an empty state."""
        s = AgentState()
        assert s.messages == []
        assert s.conversation_id == ""
        assert s.errors == []
        assert s.step == 0
        assert s.done is False

    def test_with_values(self):
        """Verify construction with explicit values."""
        s = AgentState(
            messages=[{"role": "user", "content": "hi"}],
            conversation_id="abc123",
            errors=["err1"],
            step=2,
            done=True,
        )
        assert len(s.messages) == 1
        assert s.conversation_id == "abc123"
        assert s.errors == ["err1"]
        assert s.step == 2
        assert s.done is True


# ============================================================================
# _msg_key tests
# ============================================================================

class TestMsgKey:
    """Message dedup key generation."""

    def test_format(self):
        """Verify key format: role:content_prefix."""
        key = _msg_key({"role": "user", "content": "Hello world"})
        assert key == "user:Hello world"

    def test_truncates_long_content(self):
        """Verify content is truncated to 50 chars."""
        long = "x" * 100
        key = _msg_key({"role": "assistant", "content": long})
        assert len(key) == len("assistant:") + 50

    def test_without_content(self):
        """Verify it handles missing content gracefully."""
        key = _msg_key({"role": "system"})
        assert key == "system:"


# ============================================================================
# build_messages tests
# ============================================================================

class TestBuildMessages:
    """OpenAI-format message builder."""

    def test_empty_state(self, cfg):
        """Only system prompt when state is empty."""
        state = AgentState()
        msgs = build_messages(state, cfg.system_prompt)
        assert len(msgs) == 1
        assert msgs[0] == {"role": "system", "content": cfg.system_prompt}

    def test_user_and_assistant(self, cfg):
        """User and assistant messages are preserved."""
        state = AgentState(messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ])
        msgs = build_messages(state, cfg.system_prompt)
        assert len(msgs) == 3  # system + user + assistant
        assert msgs[1] == {"role": "user", "content": "Hello"}
        assert msgs[2] == {"role": "assistant", "content": "Hi there"}

    def test_with_tool_calls(self, cfg):
        """Assistant message with tool_calls preserves the field."""
        state = AgentState(messages=[
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "test", "arguments": "{}"}}],
            }
        ])
        msgs = build_messages(state, cfg.system_prompt)
        assert len(msgs) == 2
        assert "tool_calls" in msgs[1]

    def test_tool_result_message(self, cfg):
        """Tool result messages include tool_call_id and name."""
        state = AgentState(messages=[
            {"role": "tool", "content": '{"ok": true}', "tool_call_id": "c1", "name": "test_tool"},
        ])
        msgs = build_messages(state, cfg.system_prompt)
        assert len(msgs) == 2
        assert msgs[1]["role"] == "tool"
        assert msgs[1]["tool_call_id"] == "c1"
        assert msgs[1]["name"] == "test_tool"
        assert msgs[1]["content"] == '{"ok": true}'


# ============================================================================
# call_llm tests (mocked httpx)
# ============================================================================

class TestCallLLM:
    """LLM API call with mocked HTTP client."""

    pytestmark = pytest.mark.asyncio

    def _make_mock_client(self, response_data, status_code=200):
        """Build a mock httpx.AsyncClient that returns the given response.

        NOTE: httpx.Response.json() is synchronous, so we use MagicMock, not AsyncMock.
        """
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = response_data
        mock_resp.text = json.dumps(response_data) if isinstance(response_data, dict) else str(response_data)
        if status_code != 200:
            mock_resp.raise_for_status.side_effect = Exception(f"{status_code} Error")

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_resp)
        return mock_client

    @patch("src.mcp.agent.engine.httpx.AsyncClient")
    async def test_success(self, mock_client_cls, cfg, text_only_response):
        """Verify successful LLM call returns response JSON."""
        mock_client = self._make_mock_client(text_only_response)
        mock_client_cls.return_value = mock_client

        result = await call_llm(cfg, [{"role": "user", "content": "hi"}])

        assert result == text_only_response
        mock_client.post.assert_called_once()

    @patch("src.mcp.agent.engine.httpx.AsyncClient")
    async def test_with_tools(self, mock_client_cls, cfg, tool_call_response):
        """Verify tools are included in the request body when passed."""
        mock_client = self._make_mock_client(tool_call_response)
        mock_client_cls.return_value = mock_client

        tools = [{"type": "function", "function": {"name": "create_article"}}]
        result = await call_llm(cfg, [{"role": "user", "content": "hi"}], tools=tools)

        assert result == tool_call_response
        # Verify tools were included in the POST body
        call_kwargs = mock_client.post.call_args.kwargs
        assert "tools" in call_kwargs["json"]

    @patch("src.mcp.agent.engine.httpx.AsyncClient")
    async def test_failure_raises(self, mock_client_cls, cfg):
        """Verify non-200 status raises HTTPStatusError."""
        mock_client = self._make_mock_client({}, status_code=401)
        mock_client_cls.return_value = mock_client

        with pytest.raises(Exception):
            await call_llm(cfg, [{"role": "user", "content": "hi"}])

    @patch("src.mcp.agent.engine.httpx.AsyncClient")
    async def test_empty_api_key(self, mock_client_cls):
        """Verify empty API key doesn't add Authorization header."""
        cfg_no_key = LLMConfig(
            endpoint="https://test.com",
            api_key="",
            model="test-model",
        )
        mock_client = self._make_mock_client({"choices": [{"message": {"content": "ok"}}]})
        mock_client_cls.return_value = mock_client

        await call_llm(cfg_no_key, [{"role": "user", "content": "hi"}])

        call_kwargs = mock_client.post.call_args.kwargs
        assert "Authorization" not in call_kwargs.get("headers", {})

    @patch("src.mcp.agent.engine.httpx.AsyncClient")
    async def test_correct_endpoint_url(self, mock_client_cls, cfg):
        """Verify the URL is constructed correctly (/chat/completions)."""
        mock_client = self._make_mock_client({"choices": [{"message": {"content": "ok"}}]})
        mock_client_cls.return_value = mock_client

        await call_llm(cfg, [{"role": "user", "content": "hi"}])

        called_url = mock_client.post.call_args.args[0]
        assert called_url == "https://fake-llm.example.com/chat/completions"


# ============================================================================
# execute_mcp_tool tests (mocked mcp_server)
# ============================================================================

class TestExecuteMCPTool:
    """MCP tool execution through the server."""

    pytestmark = pytest.mark.asyncio

    @patch("src.mcp.agent.engine.mcp_server")
    async def test_success(self, mock_server):
        """Verify successful tool execution returns formatted result."""
        mock_server.handle_request = AsyncMock(return_value={
            "result": {
                "content": [{"type": "text", "text": json.dumps({"success": True, "message": "Done"})}],
            }
        })

        result = await execute_mcp_tool("create_article", {"title": "Test"})

        assert "success" in result
        assert "Done" in result
        # Verify the request format
        req = mock_server.handle_request.call_args.args[0]
        assert req["method"] == "tools/call"
        assert req["params"]["name"] == "create_article"

    @patch("src.mcp.agent.engine.mcp_server")
    async def test_error_response(self, mock_server):
        """Verify tool error is properly propagated."""
        mock_server.handle_request = AsyncMock(return_value={
            "error": {"message": "Tool not found: unknown_tool"},
        })

        result = await execute_mcp_tool("unknown_tool", {})

        assert "error" in result
        assert "Tool not found" in result

    @patch("src.mcp.agent.engine.mcp_server")
    async def test_non_json_response(self, mock_server):
        """Verify non-JSON text response is returned as-is."""
        mock_server.handle_request = AsyncMock(return_value={
            "result": {
                "content": [{"type": "text", "text": "plain text result"}],
            }
        })

        result = await execute_mcp_tool("test_tool", {})

        assert result == "plain text result"


# ============================================================================
# get_tool_defs tests
# ============================================================================

class TestGetToolDefs:
    """Tool definitions proxy."""

    @patch("src.mcp.agent.engine.mcp_server")
    def test_returns_list(self, mock_server):
        """Verify get_tool_defs returns the list from mcp_server."""
        mock_server.get_openai_tools.return_value = [
            {"type": "function", "function": {"name": "create_article"}},
        ]
        tools = get_tool_defs()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "create_article"


# ============================================================================
# run_agent tests (mocked call_llm at module level)
# ============================================================================

class TestRunAgent:
    """Full agent ReAct loop — text-only, tool calls, error handling."""

    pytestmark = pytest.mark.asyncio

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_returns_text_directly(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages, text_only_response
    ):
        """When LLM returns text with no tool calls, return immediately."""
        mock_get_tools.return_value = []
        mock_call_llm.return_value = text_only_response

        state = await run_agent(cfg, sample_messages)

        assert state.done is True
        assert len(state.messages) == 2  # original user + assistant response
        assert state.messages[-1]["content"] == "Here is a blog post about AI..."
        assert state.errors == []

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_single_tool_round(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages, tool_call_response
    ):
        """When LLM returns tool calls, execute them and get final text."""
        text_resp = {
            "choices": [{"message": {"content": "Article created successfully!"}}]
        }
        mock_get_tools.return_value = [{"type": "function", "function": {"name": "create_article"}}]
        mock_call_llm.side_effect = [tool_call_response, text_resp]

        with patch("src.mcp.agent.engine.execute_mcp_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"success": true, "article_id": 42}'

            state = await run_agent(cfg, sample_messages)

            assert state.done is True
            # user msg + assistant(tool_call) + tool result + assistant(final)
            assert len(state.messages) == 4
            assert state.messages[-1]["content"] == "Article created successfully!"
            mock_exec.assert_called_once_with("create_article", {"title": "AI in 2026", "content": "Content here", "status": "draft"})

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_llm_failure_sets_error(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages
    ):
        """When LLM call fails, state captures the error and returns."""
        mock_get_tools.return_value = []
        mock_call_llm.side_effect = Exception("Connection timeout")

        state = await run_agent(cfg, sample_messages)

        assert state.done is True
        assert len(state.errors) == 1
        assert "Connection timeout" in state.errors[0]

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_json_decode_error_in_tool_args(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages
    ):
        """When tool arguments are not valid JSON, they become {}."""
        bad_args_response = {
            "choices": [
                {
                    "message": {
                        "content": "Let me try",
                        "tool_calls": [
                            {
                                "id": "call_bad",
                                "type": "function",
                                "function": {
                                    "name": "create_article",
                                    "arguments": "not-valid-json{{{",
                                },
                            }
                        ],
                    }
                }
            ]
        }
        text_resp = {
            "choices": [{"message": {"content": "Fixed it."}}]
        }
        mock_get_tools.return_value = [{"type": "function", "function": {"name": "create_article"}}]
        mock_call_llm.side_effect = [bad_args_response, text_resp]

        with patch("src.mcp.agent.engine.execute_mcp_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"success": true}'

            state = await run_agent(cfg, sample_messages)

            assert state.done is True
            # With bad JSON, args should be {} (empty dict)
            mock_exec.assert_called_once_with("create_article", {})

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_max_rounds(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages, tool_call_response
    ):
        """When max_tool_rounds is reached, agent stops."""
        limited_cfg = LLMConfig(
            endpoint="https://fake-llm.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
            max_tool_rounds=2,
        )
        mock_get_tools.return_value = [{"type": "function", "function": {"name": "create_article"}}]
        # Keep returning tool calls so the loop hits max rounds
        mock_call_llm.return_value = tool_call_response

        with patch("src.mcp.agent.engine.execute_mcp_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"success": true}'

            state = await run_agent(limited_cfg, sample_messages)

            assert state.done is True
            # Should have done 2 rounds (the for loop ends; state.done is set)
            assert state.step == 2


# ============================================================================
# stream_agent tests (mocked call_llm at module level)
# ============================================================================

class TestStreamAgent:
    """Streaming agent async generator — event types and ordering."""

    pytestmark = pytest.mark.asyncio

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_returns_text_token_then_done(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages, text_only_response
    ):
        """Direct text response: yields token then done."""
        mock_get_tools.return_value = []
        mock_call_llm.return_value = text_only_response

        events = [e async for e in stream_agent(cfg, sample_messages)]

        assert len(events) == 2
        assert events[0]["type"] == "token"
        assert events[0]["content"] == "Here is a blog post about AI..."
        assert events[1]["type"] == "done"
        assert events[1]["content"] == "Here is a blog post about AI..."

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_tool_call_events(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages, tool_call_response
    ):
        """Tool call: yields token, tool_call, tool_result, second token, then done."""
        text_resp = {
            "choices": [{"message": {"content": "All done!"}}]
        }
        mock_get_tools.return_value = [{"type": "function", "function": {"name": "create_article"}}]
        mock_call_llm.side_effect = [tool_call_response, text_resp]

        with patch("src.mcp.agent.engine.execute_mcp_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"success": true, "article_id": 42}'

            events = [e async for e in stream_agent(cfg, sample_messages)]

            # Events: token, tool_call, tool_result, token(2nd round), done
            assert len(events) == 5
            assert events[0]["type"] == "token"
            assert events[1]["type"] == "tool_call"
            assert events[1]["name"] == "create_article"
            assert events[2]["type"] == "tool_result"
            assert events[2]["name"] == "create_article"
            assert "article_id" in events[2]["content"]
            assert events[3]["type"] == "token"
            assert events[3]["content"] == "All done!"
            assert events[4]["type"] == "done"

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_two_tool_calls_in_one_round(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages, two_tool_call_response
    ):
        """Multiple tool calls in one round: each yields tool_call + tool_result."""
        text_resp = {
            "choices": [{"message": {"content": "Both tasks done."}}]
        }
        mock_get_tools.return_value = [
            {"type": "function", "function": {"name": "create_article"}},
            {"type": "function", "function": {"name": "get_system_stats"}},
        ]
        mock_call_llm.side_effect = [two_tool_call_response, text_resp]

        with patch("src.mcp.agent.engine.execute_mcp_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"success": true}'

            events = [e async for e in stream_agent(cfg, sample_messages)]

            # Filter out token/done to inspect tool events
            tool_events = [e for e in events if e["type"] in ("tool_call", "tool_result")]
            assert len(tool_events) == 4  # 2 calls + 2 results
            # tool_calls come first (both yielded before execution), then tool_results
            assert tool_events[0] == {"type": "tool_call", "name": "create_article", "args": {"title": "T1", "content": "C1"}}
            assert tool_events[1] == {"type": "tool_call", "name": "get_system_stats", "args": {}}
            assert tool_events[2]["type"] == "tool_result"
            assert tool_events[3]["type"] == "tool_result"

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_error_yields_error_event(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages
    ):
        """LLM failure yields error event then stops."""
        mock_get_tools.return_value = []
        mock_call_llm.side_effect = Exception("Rate limit exceeded")

        events = [e async for e in stream_agent(cfg, sample_messages)]

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "Rate limit" in events[0]["message"]

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_max_rounds_stops_stream(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages, tool_call_response
    ):
        """When max_tool_rounds is reached, stream yields done."""
        limited_cfg = LLMConfig(
            endpoint="https://fake-llm.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
            max_tool_rounds=1,
        )
        mock_get_tools.return_value = [{"type": "function", "function": {"name": "create_article"}}]
        mock_call_llm.return_value = tool_call_response

        with patch("src.mcp.agent.engine.execute_mcp_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"success": true}'

            events = [e async for e in stream_agent(limited_cfg, sample_messages)]

            # After one tool round, no more LLM calls → yields done
            assert events[-1]["type"] == "done"

    @patch("src.mcp.agent.engine.call_llm")
    @patch("src.mcp.agent.engine.get_tool_defs")
    async def test_tool_args_json_decode_error(
        self, mock_get_tools, mock_call_llm, cfg, sample_messages
    ):
        """Bad JSON in tool args: args become {}, tool still called."""
        bad_json_response = {
            "choices": [
                {
                    "message": {
                        "content": "Trying...",
                        "tool_calls": [
                            {
                                "id": "c_bad",
                                "type": "function",
                                "function": {
                                    "name": "test_tool",
                                    "arguments": "NOT JSON!!@#",
                                },
                            }
                        ],
                    }
                }
            ]
        }
        text_resp = {
            "choices": [{"message": {"content": "Fixed."}}]
        }
        mock_get_tools.return_value = [{"type": "function", "function": {"name": "test_tool"}}]
        mock_call_llm.side_effect = [bad_json_response, text_resp]

        with patch("src.mcp.agent.engine.execute_mcp_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "ok"

            events = [e async for e in stream_agent(cfg, sample_messages)]

            # tool_call event should have empty args
            tool_call_event = [e for e in events if e["type"] == "tool_call"][0]
            assert tool_call_event["args"] == {}
            mock_exec.assert_called_once_with("test_tool", {})
