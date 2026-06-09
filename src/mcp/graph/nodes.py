"""
LangGraph-style node functions for the MCP graph.

Each node is an async function:  async fn(state: dict, ctx: ExecutionContext) -> dict | Command | None
- Return a dict to merge into state.
- Return Command(goto=..., update=...) for control flow.
- Return None to leave state unchanged.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from src.mcp.graph.engine import (
    ExecutionContext, Command, END,
)
from src.mcp.server import mcp_server

logger = logging.getLogger('mcp_graph.nodes')

# ─── Helpers ────────────────────────────────────────────────────────

def _build_openai_messages(state: Dict, system_prompt: str) -> List[Dict]:
    """Build OpenAI-format message list with proper content handling."""
    messages = [{"role": "system", "content": system_prompt or "You are a helpful AI assistant."}]
    for msg in state.get("messages", []):
        role = msg.get("role", "user")
        entry: Dict[str, Any] = {"role": role}
        content_val = msg.get("content")
        if role in ("tool", "user"):
            entry["content"] = content_val or ""
        else:
            entry["content"] = content_val
        if msg.get("tool_calls"):
            entry["tool_calls"] = msg["tool_calls"]
        if msg.get("tool_call_id"):
            entry["tool_call_id"] = msg["tool_call_id"]
        if msg.get("name"):
            entry["name"] = msg["name"]
        messages.append(entry)
    return messages


async def _call_llm(
    endpoint: str, api_key: str, model: str,
    messages: List[Dict], tools: Optional[List] = None,
    max_tokens: int = 4096, temperature: float = 0.7,
) -> Dict:
    import httpx
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if tools:
        body["tools"] = tools
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    msg_summary = [(m.get("role"), len(str(m.get("content","")) or ""), bool(m.get("tool_calls"))) for m in messages]
    logger.info(f"LLM call: model={model} msg_count={len(messages)} tools={len(tools) if tools else 0}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{endpoint.rstrip('/')}/chat/completions", json=body, headers=headers)
        if resp.status_code != 200:
            logger.error(f"LLM API error {resp.status_code}: {resp.text[:1000]}")
        resp.raise_for_status()
        return resp.json()


# ─── Input Processing ───────────────────────────────────────────────

async def input_node(state: Dict, ctx: ExecutionContext) -> Optional[Dict]:
    """Validate and preprocess user input."""
    messages = state.get("messages", [])
    if messages:
        last = messages[-1]
        if isinstance(last.get("content"), str):
            last["content"] = last["content"].strip()
            if not last["content"]:
                state.setdefault("errors", []).append("Empty message")
    return None  # no state update


# ─── LLM Agent ──────────────────────────────────────────────────────

async def agent_node(state: Dict, ctx: ExecutionContext) -> Dict:
    """
    LLM-powered agent. Calls the configured LLM once.
    Returns the LLM response. Router decides next step.
    """
    endpoint = ctx.extra.get("llm_endpoint", "")
    api_key = ctx.extra.get("llm_api_key", "")
    model = ctx.extra.get("llm_model", "gpt-4o-mini")
    system_prompt = ctx.extra.get("system_prompt", "You are a helpful AI assistant.")
    tools = mcp_server.get_openai_tools()

    openai_messages = _build_openai_messages(state, system_prompt)

    try:
        response = await _call_llm(
            endpoint=endpoint, api_key=api_key, model=model,
            messages=openai_messages,
            tools=tools,
        )
    except Exception as e:
        err = str(e)
        logger.error(f"LLM call failed: {err}")
        state.setdefault("messages", []).append({"role": "assistant", "content": f"❌ LLM 调用失败：{err}"})
        state.setdefault("errors", []).append(f"LLM error: {err}")
        return {}

    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content") or ""
    tool_calls = message.get("tool_calls")

    state.setdefault("messages", []).append({
        "role": "assistant",
        "content": content or None,
        "tool_calls": tool_calls,
    })

    return {"messages": state["messages"]}


# ─── Tool Execution ─────────────────────────────────────────────────

async def execute_tools_node(state: Dict, ctx: ExecutionContext) -> Dict:
    """
    Execute tool calls from the last assistant message.
    Returns back to agent for continued reasoning.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    last = messages[-1]
    tool_calls = last.get("tool_calls", [])
    if not tool_calls:
        return {}

    for tc in tool_calls:
        func_name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"]["arguments"])
        except json.JSONDecodeError:
            args = {}

        mcp_req = {"method": "tools/call", "params": {"name": func_name, "arguments": args}, "id": tc.get("id", "")}
        result = await mcp_server.handle_request(mcp_req)

        if "error" in result:
            result_text = json.dumps({"error": result["error"]["message"]}, ensure_ascii=False)
        else:
            content_list = result.get("result", {}).get("content", [])
            result_text = content_list[0].get("text", "{}") if content_list else "{}"

        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result_text, "name": func_name})

    return {"messages": messages, "tool_calls_used": len(tool_calls)}


# ─── Output Formatting ──────────────────────────────────────────────

async def output_node(state: Dict, ctx: ExecutionContext) -> Optional[Dict]:
    """Ensure the last message is from the assistant."""
    messages = state.get("messages", [])
    if messages and messages[-1].get("role") != "assistant":
        messages.append({"role": "assistant", "content": "操作已完成。还有什么我可以帮你的吗？"})
        return {"messages": messages}
    return None


# ─── Graph Builder ──────────────────────────────────────────────────

def build_chat_graph() -> 'Graph':
    """Build the default AI chat agent graph (langgraph-style)."""
    from src.mcp.graph.engine import Graph, END

    graph = Graph(id="fastblog-chat")
    graph.metadata["description"] = "AI Chat agent with MCP tools"

    graph.add_node("input", input_node)
    graph.add_node("agent", agent_node)
    graph.add_node("execute_tools", execute_tools_node)
    graph.add_node("output", output_node)

    graph.set_entry_point("input")
    graph.add_edge("input", "agent")
    graph.add_edge("agent", "execute_tools",
                   condition=lambda ctx: bool(ctx.get("messages") and any(
                       m.get("tool_calls") for m in reversed(ctx.get("messages", []))
                       if m.get("role") == "assistant"
                   )) and "execute_tools")
    graph.add_edge("execute_tools", "agent")  # loop back: tools → agent for next reasoning
    graph.add_edge("agent", "output",
                   condition=lambda ctx: not any(
                       m.get("tool_calls") for m in ctx.get("messages", [])
                       if m.get("role") == "assistant"
                   ) and "output")

    return graph
