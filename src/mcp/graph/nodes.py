"""
Built-in nodes for the MCP graph engine.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from src.mcp.graph.engine import (
    Node, NodeType, State, ExecutionContext, SubgraphNode,
)
from src.mcp.server import mcp_server

logger = logging.getLogger('mcp_graph.nodes')


# ─── InputNode ──────────────────────────────────────────────────────

class InputNode(Node):
    """Validates and preprocesses user input."""

    def __init__(self, id: str = "input", label: str = "Input"):
        super().__init__(id, label=label, node_type=NodeType.INPUT)

    async def run(self, state: State, ctx: ExecutionContext) -> State:
        # Trim whitespace from messages
        for msg in state.messages:
            if isinstance(msg.get('content'), str):
                msg['content'] = msg['content'].strip()
        # Check for empty input
        if state.messages and not state.messages[-1].get('content', '').strip():
            state.errors.append("Empty message content")
        return state


# ─── OutputNode ─────────────────────────────────────────────────────

class OutputNode(Node):
    """Formats and finalizes output."""

    def __init__(self, id: str = "output", label: str = "Output"):
        super().__init__(id, label=label, node_type=NodeType.OUTPUT)

    async def run(self, state: State, ctx: ExecutionContext) -> State:
        # Ensure last message is from assistant
        if state.messages and state.messages[-1].get('role') != 'assistant':
            state.messages.append({
                "role": "assistant",
                "content": "操作已完成。还有什么我可以帮你的吗？",
            })
        return state


# ─── ToolNode ───────────────────────────────────────────────────────

class ToolNode(Node):
    """Executes a single MCP tool."""

    def __init__(
        self,
        id: str,
        tool_name: str,
        label: str = "",
        param_mapping: Optional[Dict[str, str]] = None,
    ):
        super().__init__(id, label=label or f"Tool: {tool_name}", node_type=NodeType.TOOL)
        self.tool_name = tool_name
        self.param_mapping = param_mapping or {}

    async def run(self, state: State, ctx: ExecutionContext) -> State:
        # Extract arguments from state or tool_results
        arguments = {}
        for tool_param, state_path in self.param_mapping.items():
            arguments[tool_param] = self._resolve(state, state_path)

        # Call MCP tool
        mcp_request = {
            "method": "tools/call",
            "params": {"name": self.tool_name, "arguments": arguments},
            "id": f"graph-{state.step}",
        }
        response = await mcp_server.handle_request(mcp_request)

        if "error" in response:
            error_msg = response["error"]["message"]
            state.errors.append(f"Tool '{self.tool_name}' failed: {error_msg}")
            state.tool_results[self.tool_name] = {"error": error_msg}
        else:
            content = response.get("result", {}).get("content", [])
            result_text = content[0].get("text", "{}") if content else "{}"
            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                result_data = {"raw": result_text}
            state.tool_results[self.tool_name] = result_data

        return state


# ─── MCPToolNode ────────────────────────────────────────────────────

class MCPToolNode(Node):
    """
    Flexible tool execution node.
    Reads tool calls from the last assistant message and executes them.
    This is the primary node used in the chat graph.
    """

    def __init__(self, id: str = "execute_tools", label: str = "Execute Tools"):
        super().__init__(id, label=label, node_type=NodeType.TOOL)

    async def run(self, state: State, ctx: ExecutionContext) -> State:
        if not state.messages:
            return state

        last_msg = state.messages[-1]
        tool_calls = last_msg.get("tool_calls", [])
        if not tool_calls:
            return state

        for tc in tool_calls:
            func_name = tc.get("function", {}).get("name", "")
            try:
                arguments = json.loads(tc.get("function", {}).get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}

            logger.info(f"[MCPTool] Executing: {func_name} with {arguments}")

            mcp_request = {
                "method": "tools/call",
                "params": {"name": func_name, "arguments": arguments},
                "id": tc.get("id", f"tool-{state.step}"),
            }
            response = await mcp_server.handle_request(mcp_request)

            if "error" in response:
                error_msg = response["error"]["message"]
                result = {"error": error_msg}
                state.errors.append(f"Tool '{func_name}' failed: {error_msg}")
            else:
                content = response.get("result", {}).get("content", [])
                result_text = content[0].get("text", "{}") if content else "{}"
                try:
                    result = json.loads(result_text)
                except json.JSONDecodeError:
                    result = {"raw": result_text}

            # Add tool result message to conversation
            state.messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": json.dumps(result, ensure_ascii=False, default=str),
                "name": func_name,
            })
            state.tool_results[func_name] = result

        return state


# ─── AgentNode ──────────────────────────────────────────────────────

class AgentNode(Node):
    """
    LLM-powered agent node.
    Calls the configured LLM, processes tool calls, and streams response.
    """

    def __init__(
        self,
        id: str = "agent",
        label: str = "Agent",
        system_prompt: Optional[str] = None,
        max_tool_rounds: int = 5,
    ):
        super().__init__(id, label=label, node_type=NodeType.AGENT)
        self.system_prompt = system_prompt
        self.max_tool_rounds = max_tool_rounds

    async def run(self, state: State, ctx: ExecutionContext) -> State:
        endpoint = ctx.extra.get("llm_endpoint", "")
        api_key = ctx.extra.get("llm_api_key", "")
        model = ctx.extra.get("llm_model", "gpt-4o-mini")
        system_prompt = ctx.extra.get("system_prompt", self.system_prompt or "You are a helpful AI assistant.")
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant."
        tools = mcp_server.get_openai_tools()

        # Build OpenAI-style messages
        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in state.messages:
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
            openai_messages.append(entry)

        for _round in range(self.max_tool_rounds):
            try:
                response = await self._call_llm(
                    endpoint=endpoint, api_key=api_key, model=model,
                    messages=openai_messages,
                    tools=tools if _round == 0 else None,
                )
            except Exception as e:
                err = str(e)
                logger.error(f"[run] LLM call failed: {err}")
                state.messages.append({"role": "assistant", "content": f"❌ LLM 调用失败：{err}"})
                state.errors.append(f"LLM error: {err}")
                break

            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                state.messages.append({"role": "assistant", "content": content})
                break

            state.messages.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})
            openai_messages.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})

            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}

                mcp_req = {
                    "method": "tools/call",
                    "params": {"name": func_name, "arguments": args},
                    "id": tc.get("id", ""),
                }
                result = await mcp_server.handle_request(mcp_req)

                if "error" in result:
                    result_text = json.dumps({"error": result["error"]["message"]}, ensure_ascii=False)
                else:
                    content_list = result.get("result", {}).get("content", [])
                    result_text = content_list[0].get("text", "{}") if content_list else "{}"

                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_text,
                    "name": func_name,
                }
                state.messages.append(tool_msg)
                openai_messages.append(tool_msg)

        return state

    async def stream(self, state: State, ctx: ExecutionContext) -> AsyncGenerator[State, None]:
        """Stream agent execution with per-chunk state updates."""
        endpoint = ctx.extra.get("llm_endpoint", "")
        api_key = ctx.extra.get("llm_api_key", "")
        model = ctx.extra.get("llm_model", "gpt-4o-mini")
        system_prompt = ctx.extra.get("system_prompt", self.system_prompt or "You are a helpful AI assistant.")
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant."
        tools = mcp_server.get_openai_tools()

        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in state.messages:
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
            openai_messages.append(entry)

        for _round in range(self.max_tool_rounds):
            try:
                response = await self._call_llm(
                    endpoint=endpoint, api_key=api_key, model=model,
                    messages=openai_messages,
                    tools=tools if _round == 0 else None,
                )
            except Exception as e:
                err = str(e)
                logger.error(f"[stream] LLM call failed: {err}")
                state.messages.append({"role": "assistant", "content": f"❌ LLM 调用失败：{err}"})
                state.errors.append(f"LLM error: {err}")
                yield state
                break

            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}

                mcp_req = {
                    "method": "tools/call",
                    "params": {"name": func_name, "arguments": args},
                    "id": tc.get("id", ""),
                }
                result = await mcp_server.handle_request(mcp_req)

                if "error" in result:
                    result_text = json.dumps({"error": result["error"]["message"]}, ensure_ascii=False)
                else:
                    content_list = result.get("result", {}).get("content", [])
                    result_text = content_list[0].get("text", "{}") if content_list else "{}"

                tool_msg = {"role": "tool", "tool_call_id": tc["id"], "content": result_text, "name": func_name}
                state.messages.append(tool_msg)
                openai_messages.append(tool_msg)

    async def _call_llm(self, endpoint: str, api_key: str, model: str,
                         messages: List[Dict], tools: Optional[List] = None,
                         max_tokens: int = 4096, temperature: float = 0.7) -> Dict:
        import httpx
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if tools:
            body["tools"] = tools
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Debug log (truncated)
        msg_summary = [(m.get("role"), len(m.get("content","") or ""), bool(m.get("tool_calls"))) for m in messages]
        logger.info(f"LLM call: model={model} messages={msg_summary} tools={len(tools) if tools else 0}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{endpoint.rstrip('/')}/chat/completions", json=body, headers=headers)
            if resp.status_code != 200:
                logger.error(f"LLM API error {resp.status_code}: {resp.text[:1000]}")
            resp.raise_for_status()
            return resp.json()


# ─── RouterNode ─────────────────────────────────────────────────────

class RouterNode(Node):
    """
    Decides which node to go to next based on the current state.
    Useful for conditional branching in the graph.
    """

    def __init__(
        self,
        id: str = "router",
        label: str = "Router",
        routes: Optional[Dict[str, str]] = None,
        default_route: str = "output",
    ):
        """
        Args:
            routes: Dict of {condition_name: target_node_id}
            default_route: fallback if no condition matches
        """
        super().__init__(id, label=label, node_type=NodeType.ROUTER)
        self.routes = routes or {}
        self.default_route = default_route

    async def run(self, state: State, ctx: ExecutionContext) -> State:
        """Router just emits its decision via state metadata."""
        next_node = self._decide(state)
        state.metadata["next_node"] = next_node
        return state

    def _decide(self, state: State) -> str:
        """Determine the next node. Override in subclasses."""
        # Default: check for tool calls in last message
        if state.messages:
            last = state.messages[-1]
            if last.get("tool_calls"):
                return self.routes.get("has_tools", "execute_tools")
        return self.default_route


# ─── Graph Builders ─────────────────────────────────────────────────

def build_chat_graph() -> 'Graph':
    """Build the default AI chat agent graph."""
    from src.mcp.graph.engine import Graph

    graph = Graph(id="fastblog-chat", metadata={"description": "AI Chat agent with MCP tools"})

    graph.add_node(InputNode("input", "User Input"))
    graph.add_node(AgentNode("agent", "AI Agent"))
    graph.add_node(MCPToolNode("tools", "Execute Tools"))
    graph.add_node(OutputNode("output", "Format Output"))
    graph.add_node(RouterNode("router", "Route Decision",
                               routes={"has_tools": "tools"},
                               default_route="output"))

    graph.set_entry_point("input")
    graph.add_edge("input", "agent")
    graph.add_edge("agent", "router")
    # Conditional routing: router stores decision in state.metadata["next_node"]
    graph.add_edge("router", "tools",
                   condition=lambda s: s.metadata.get("next_node") == "tools" and "tools")
    graph.add_edge("router", "output",
                   condition=lambda s: s.metadata.get("next_node") != "tools" and "output")
    graph.add_edge("tools", "agent")  # Loop back for multi-turn tool use

    return graph
