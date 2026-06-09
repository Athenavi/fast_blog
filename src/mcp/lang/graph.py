"""
LangGraph-based ReAct agent graph for FastBlog.

Uses langgraph's StateGraph + ToolNode + tools_condition for
a robust ReAct loop. The LLM config (endpoint/api_key/model) is
passed via RunnableConfig["configurable"].
"""

import logging
from typing import Any, Dict, Literal, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import Annotated, TypedDict

from src.mcp.lang.llm import FastBlogLLM, CFG_ENDPOINT, CFG_API_KEY, CFG_MODEL
from src.mcp.lang.tools import MCP_TOOLS

logger = logging.getLogger('mcp.lang.graph')


# ─── State ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """Graph state — extends MessagesState with custom fields."""
    messages: Annotated[list, add_messages]
    # Optional metadata stored for SSE streaming
    step: int
    current_node: str
    conversation_id: str


# ─── Graph builder ──────────────────────────────────────────────────

def build_agent() -> StateGraph:
    """Build the ReAct agent graph (compiled once, reused with different configs)."""
    llm = FastBlogLLM()
    tool_node = ToolNode(MCP_TOOLS)

    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(MCP_TOOLS)

    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("agent", _call_model)
    graph.add_node("tools", tool_node)

    # Edges
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")  # loop back

    return graph


async def _call_model(state: AgentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Call the LLM with current messages."""
    llm = FastBlogLLM()
    llm_with_tools = llm.bind_tools(MCP_TOOLS)

    messages = state["messages"]

    # If there's a system message in state, use it; otherwise the frontend should have included one
    response = await llm_with_tools.ainvoke(messages, config=config)
    return {"messages": [response], "step": state.get("step", 0) + 1, "current_node": "agent"}


async def build_compiled_agent() -> Any:
    """Build and compile the agent graph with MemorySaver checkpointing."""
    graph = build_agent()
    checkpointer = MemorySaver()
    compiled = graph.compile(checkpointer=checkpointer)
    return compiled


# ─── Helper: build RunnableConfig from user's LLM settings ─────────

def make_config(
    endpoint: str,
    api_key: str,
    model: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    thread_id: str = "default",
) -> RunnableConfig:
    """Create a RunnableConfig with LLM settings for this request."""
    return {
        "configurable": {
            CFG_ENDPOINT: endpoint,
            CFG_API_KEY: api_key,
            CFG_MODEL: model,
            CFG_MAX_TOKENS: max_tokens,
            CFG_TEMPERATURE: temperature,
            "thread_id": thread_id,
        }
    }


# ─── Convenience: one-shot agent invocation ─────────────────────────

async def run_agent(
    endpoint: str,
    api_key: str,
    model: str,
    messages: list,
    system_prompt: Optional[str] = None,
    thread_id: str = "default",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """Run the agent to completion with the given config.

    Returns the final state dict.
    """
    config = make_config(endpoint, api_key, model, max_tokens, temperature, thread_id)
    agent = await build_compiled_agent()

    # Prepend system message if provided
    input_messages = list(messages)
    if system_prompt:
        input_messages.insert(0, {"role": "system", "content": system_prompt})

    result = await agent.ainvoke(
        {"messages": input_messages, "step": 0, "conversation_id": thread_id},
        config=config,
    )
    return result


async def stream_agent(
    endpoint: str,
    api_key: str,
    model: str,
    messages: list,
    system_prompt: Optional[str] = None,
    thread_id: str = "default",
    max_tokens: int = 4096,
    temperature: float = 0.7,
):
    """Stream agent execution events.

    Yields dicts with type: "state_update" or "done" or "error".
    """
    config = make_config(endpoint, api_key, model, max_tokens, temperature, thread_id)
    agent = await build_compiled_agent()

    input_messages = list(messages)
    if system_prompt:
        input_messages.insert(0, {"role": "system", "content": system_prompt})

    try:
        async for event in agent.astream_events(
            {"messages": input_messages, "step": 0, "conversation_id": thread_id},
            config=config,
            version="v2",
        ):
            kind = event.get("event")
            if kind == "on_chat_model_stream":
                # Token-level streaming — can be used for real-time UX
                chunk = event.get("data", {}).get("chunk", {})
                if isinstance(chunk, AIMessage) and chunk.content:
                    yield {
                        "type": "token",
                        "content": chunk.content,
                    }
            elif kind == "on_chain_end":
                # Node-level end — state update available
                pass
        yield {"type": "done"}
    except Exception as e:
        logger.exception("Agent streaming error")
        yield {"type": "error", "message": str(e)}
