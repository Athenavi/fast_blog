"""
Core agent engine — LLM call, tool execution, streaming, ReAct loop.

Architecture:
  AgentLoop(state) → LLM → tool calls? → execute tools → LLM → ... → final text
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx

from src.mcp.server import mcp_server

logger = logging.getLogger("mcp.agent")


# ─── Config ─────────────────────────────────────────────────────────

@dataclass
class LLMConfig:
    """LLM connection settings."""
    endpoint: str
    api_key: str
    model: str
    system_prompt: str = "You are a helpful AI assistant."
    max_tokens: int = 4096
    temperature: float = 0.7
    max_tool_rounds: int = 10


# ─── State ──────────────────────────────────────────────────────────

@dataclass
class AgentState:
    """Mutable agent execution state."""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    conversation_id: str = ""
    errors: List[str] = field(default_factory=list)
    step: int = 0
    done: bool = False


# ─── Key ────────────────────────────────────────────────────────────

def _msg_key(msg: Dict) -> str:
    """Unique key for a message (dedup assistant messages with same role+content)."""
    return f"{msg.get('role','')}:{msg.get('content','')[:50]}"


# ─── LLM Call ──────────────────────────────────────────────────────

async def call_llm(
    cfg: LLMConfig,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """Call an OpenAI-compatible LLM endpoint. Returns the response JSON."""
    body: Dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "max_tokens": cfg.max_tokens,
        "temperature": cfg.temperature,
    }
    if tools:
        body["tools"] = tools

    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    url = f"{cfg.endpoint.rstrip('/')}/chat/completions"

    logger.info(f"LLM call: model={cfg.model} msgs={len(messages)} tools={len(tools) if tools else 0}")

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code != 200:
            logger.error(f"LLM error {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
        return resp.json()


# ─── MCP tool execution ────────────────────────────────────────────

async def execute_mcp_tool(tool_name: str, arguments: Dict) -> str:
    """Execute an MCP tool and return a readable result string."""
    req = {
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
        "id": uuid.uuid4().hex[:8],
    }
    resp = await mcp_server.handle_request(req)
    if "error" in resp:
        return json.dumps({"error": resp["error"]["message"]}, ensure_ascii=False)

    content = resp.get("result", {}).get("content", [])
    text = content[0].get("text", "{}") if content else "{}"
    try:
        data = json.loads(text)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return text


# ─── Tool definitions (OpenAI function-calling format) ─────────────

def get_tool_defs() -> List[Dict]:
    """Get MCP tools in OpenAI function-calling format."""
    return mcp_server.get_openai_tools()


# ─── Message builder ───────────────────────────────────────────────

def build_messages(state: AgentState, system_prompt: str) -> List[Dict]:
    """Build OpenAI-format messages from state.
    
    Defensively ensures every ``tool`` message carries a ``tool_call_id``
    (generates a synthetic id when the frontend ReAct loop omits it).
    """
    msgs = [{"role": "system", "content": system_prompt}]
    for m in state.messages:
        role = m.get("role", "user")
        entry: Dict[str, Any] = {"role": role}
        content = m.get("content")
        if role in ("tool", "user"):
            entry["content"] = content or ""
        else:
            entry["content"] = content
        if m.get("tool_calls"):
            entry["tool_calls"] = m["tool_calls"]
        if m.get("tool_call_id"):
            entry["tool_call_id"] = m["tool_call_id"]
        elif role == "tool":
            # 前端 ReAct 循环生成的 tool 消息可能缺少 id
            entry["tool_call_id"] = f"synthetic-{uuid.uuid4().hex[:8]}"
        if m.get("name"):
            entry["name"] = m["name"]
        msgs.append(entry)
    return msgs


# ─── Core agent execution ──────────────────────────────────────────

async def run_agent(
    cfg: LLMConfig,
    messages: List[Dict[str, Any]],
    conversation_id: str = "",
) -> AgentState:
    """Run the agent to completion. Returns final state."""
    state = AgentState(messages=list(messages), conversation_id=conversation_id or uuid.uuid4().hex[:12])

    tools = get_tool_defs()

    for _round in range(cfg.max_tool_rounds):
        openai_msgs = build_messages(state, cfg.system_prompt)

        try:
            response = await call_llm(cfg, openai_msgs, tools=tools)
        except Exception as e:
            err = str(e)[:300]
            logger.error(f"LLM call failed: {err}")
            state.errors.append(err)
            state.messages.append({"role": "assistant", "content": f"❌ 调用失败：{err}"})
            state.done = True
            return state

        choice = response.get("choices", [{}])[0]
        msg_data = choice.get("message", {})
        content = msg_data.get("content") or ""
        tool_calls = msg_data.get("tool_calls")

        if not tool_calls:
            state.messages.append({"role": "assistant", "content": content})
            state.done = True
            return state

        # Add assistant message with tool calls
        state.messages.append({
            "role": "assistant",
            "content": content or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]},
                }
                for tc in tool_calls
            ],
        })

        # Execute each tool
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}

            result_text = await execute_mcp_tool(func_name, args)

            state.messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result_text,
                "name": func_name,
            })

        state.step += 1

    state.done = True
    return state


# ─── Streaming agent execution ────────────────────────────────────

async def stream_agent(
    cfg: LLMConfig,
    messages: List[Dict[str, Any]],
    conversation_id: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream agent execution events.

    Yields dicts:
      {"type": "token", "content": "..."}       — streaming token
      {"type": "tool_call", "name": "...", "args": {...}}   — tool call started
      {"type": "tool_result", "name": "...", "content": "..."} — tool result
      {"type": "done", "content": "..."}         — complete
      {"type": "error", "message": "..."}        — error
    """
    state = AgentState(messages=list(messages), conversation_id=conversation_id or uuid.uuid4().hex[:12])
    tools = get_tool_defs()
    accumulated = ""

    for _round in range(cfg.max_tool_rounds):
        openai_msgs = build_messages(state, cfg.system_prompt)

        try:
            response = await call_llm(cfg, openai_msgs, tools=tools)
        except Exception as e:
            err = str(e)[:300]
            logger.error(f"LLM call failed: {err}")
            yield {"type": "error", "message": err}
            return

        choice = response.get("choices", [{}])[0]
        msg_data = choice.get("message", {})
        content = msg_data.get("content") or ""
        tool_calls = msg_data.get("tool_calls")

        # Stream the text content
        if content:
            accumulated += content
            yield {"type": "token", "content": content}

        if not tool_calls:
            yield {"type": "done", "content": accumulated}
            return

        # Notify about tool calls
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}
            yield {"type": "tool_call", "name": func_name, "args": args}

        # Add assistant message to state
        state.messages.append({
            "role": "assistant",
            "content": content or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]},
                }
                for tc in tool_calls
            ],
        })

        # Execute tools
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}

            result_text = await execute_mcp_tool(func_name, args)

            yield {"type": "tool_result", "name": func_name, "content": result_text}

            state.messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result_text,
                "name": func_name,
            })

        state.step += 1

    yield {"type": "done", "content": accumulated}
