"""
FastBlog MCP AI Agent API v2

Uses the MCP Graph engine for stateful, interruptable, streamable AI agent execution.
Endpoints:
  POST /api/v2/mcp/chat        — Non-streaming chat (returns final response)
  POST /api/v2/mcp/chat/stream — SSE streaming chat
  GET  /api/v2/mcp/chat/{conv_id}/checkpoints — List checkpoints
  POST /api/v2/mcp/chat/{conv_id}/backtrack  — Backtrack to a step
  POST /api/v2/mcp/chat/{conv_id}/interrupt  — Interrupt execution
  POST /api/v2/mcp/chat/{conv_id}/resume     — Resume interrupted
  DELETE /api/v2/mcp/chat/{conv_id}          — Clear conversation
  GET  /api/v2/mcp/tools      — List MCP tools
  GET  /api/v2/mcp/info       — Server info
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.mcp.graph import (
    Graph, State, Executor, build_chat_graph,
    InMemoryCheckpointer, FileCheckpointer,
    ShortTermMemory, LongTermMemory,
)
from src.mcp.server import mcp_server

logger = logging.getLogger('mcp_proxy')
router = APIRouter(prefix="/mcp", tags=["MCP AI Agent"])

# ─── Graph engine singleton ────────────────────────────────────────

_checkpointer = InMemoryCheckpointer()
_memories = [ShortTermMemory(), LongTermMemory()]
_graph = build_chat_graph()


def _get_executor() -> Executor:
    return Executor(_graph, checkpointer=_checkpointer, memories=_memories)


# ─── Request/Response models ──────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class ChatRequest(BaseModel):
    endpoint: str
    api_key: str
    model: str
    messages: List[ChatMessage]
    conversation_id: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    conversation_id: str
    message: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


# ─── Non-streaming chat ──────────────────────────────────────────

@router.post("/chat")
async def chat_non_stream(req: ChatRequest):
    """Non-streaming chat — runs graph to completion, returns final result."""
    conv_id = req.conversation_id or uuid.uuid4().hex[:12]

    # Build initial state from messages
    messages = [{"role": m.role, "content": m.content} for m in req.messages if m.content]
    state = State(messages=messages, conversation_id=conv_id)

    executor = _get_executor()
    ctx = _build_context(req)

    try:
        final_state, _ = await executor.run(state, ctx=ctx)

        # Extract last assistant message
        assistant_msgs = [m for m in final_state.messages if m.get("role") == "assistant"]
        last_content = assistant_msgs[-1].get("content", "") if assistant_msgs else ""
        last_tool_calls = assistant_msgs[-1].get("tool_calls") if assistant_msgs else None

        return ChatResponse(
            success=not bool(final_state.errors),
            conversation_id=conv_id,
            content=last_content,
            tool_calls=last_tool_calls,
            message=final_state.errors[-1] if final_state.errors else None,
        )
    except Exception as e:
        logger.exception("Chat non-stream error")
        raise HTTPException(status_code=500, detail=str(e))


# ─── SSE streaming chat ──────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming chat — yields state updates as Server-Sent Events."""
    conv_id = req.conversation_id or uuid.uuid4().hex[:12]

    messages = [{"role": m.role, "content": m.content} for m in req.messages if m.content]
    state = State(messages=messages, conversation_id=conv_id)

    executor = _get_executor()
    ctx = _build_context(req)

    async def event_generator():
        try:
            async for current_state, cid in executor.stream(state, ctx=ctx):
                # Find the latest assistant message delta
                assistant_msgs = [m for m in current_state.messages if m.get("role") == "assistant"]
                tool_msgs = [m for m in current_state.messages if m.get("role") == "tool"]

                payload = {
                    "type": "state_update",
                    "conversation_id": conv_id,
                    "step": current_state.step,
                    "current_node": current_state.current_node,
                    "checkpoint_id": cid,
                    "has_errors": bool(current_state.errors),
                    "errors": current_state.errors[-1:] if current_state.errors else [],
                    "assistant_content": assistant_msgs[-1].get("content", "") if assistant_msgs else None,
                    "tool_calls": assistant_msgs[-1].get("tool_calls") if assistant_msgs else None,
                    "tool_results": {k: v for k, v in current_state.tool_results.items()},
                    "messages_count": len(current_state.messages),
                    "interrupted": current_state.interrupted,
                }

                yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"

            # Final done event
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception("Streaming error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
        },
    )


# ─── Checkpoints & State management ──────────────────────────────

@router.get("/chat/{conv_id}/checkpoints")
async def list_checkpoints(conv_id: str):
    """List all checkpoints for a conversation."""
    executor = _get_executor()
    checkpoints = await executor.list_checkpoints(conv_id)
    return {"success": True, "data": checkpoints}


@router.post("/chat/{conv_id}/backtrack")
async def backtrack(conv_id: str, step: int = Query(..., description="Target step number")):
    """Backtrack to a specific step."""
    executor = _get_executor()
    state = await executor.backtrack(conv_id, step)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No checkpoint found at step {step}")
    # Restore messages up to that point
    return {
        "success": True,
        "data": {
            "step": state.step,
            "messages": state.messages,
            "has_errors": bool(state.errors),
        },
    }


@router.post("/chat/{conv_id}/interrupt")
async def interrupt(conv_id: str, reason: str = "User interrupted"):
    """Interrupt a running conversation."""
    executor = _get_executor()
    ok = await executor.interrupt(conv_id, reason)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No active conversation '{conv_id}'")
    return {"success": True, "message": "Interrupted"}


@router.post("/chat/{conv_id}/resume")
async def resume_conversation(conv_id: str, req: ChatRequest):
    """Resume an interrupted conversation with new input."""
    executor = _get_executor()

    if not req.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    last_user_msg = req.messages[-1].content or ""
    if not last_user_msg.strip():
        raise HTTPException(status_code=400, detail="Last message must have content")

    async def event_generator():
        try:
            async for current_state, cid in executor.resume(conv_id, last_user_msg):
                assistant_msgs = [m for m in current_state.messages if m.get("role") == "assistant"]
                payload = {
                    "type": "resume_update",
                    "conversation_id": conv_id,
                    "step": current_state.step,
                    "checkpoint_id": cid,
                    "assistant_content": assistant_msgs[-1].get("content", "") if assistant_msgs else None,
                    "tool_calls": assistant_msgs[-1].get("tool_calls") if assistant_msgs else None,
                    "interrupted": current_state.interrupted,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.delete("/chat/{conv_id}")
async def clear_conversation(conv_id: str):
    """Delete a conversation and its checkpoints."""
    await _checkpointer.delete(conv_id)
    for mem in _memories:
        await mem.clear(conv_id)
    return {"success": True, "message": f"Conversation '{conv_id}' cleared"}


# ─── MCP info endpoints ──────────────────────────────────────────

@router.get("/tools")
async def list_mcp_tools():
    """List MCP tools in OpenAI function-calling format."""
    return {"success": True, "data": mcp_server.get_openai_tools()}


@router.get("/info")
async def mcp_proxy_info():
    """Get MCP proxy and graph info."""
    info = mcp_server.get_server_info()
    info["graph_id"] = _graph.id
    info["graph_nodes"] = list(_graph.nodes.keys())
    info["graph_edges"] = [f"{e.source}→{e.target}" for e in _graph.edges]
    return {"success": True, "data": info}


# ─── Helper ──────────────────────────────────────────────────────

def _build_context(req: ChatRequest) -> 'ExecutionContext':
    from src.mcp.graph.engine import ExecutionContext
    return ExecutionContext(
        graph=_graph,
        checkpointer=_checkpointer,
        memories=_memories,
        extra={
            "llm_endpoint": req.endpoint,
            "llm_api_key": req.api_key,
            "llm_model": req.model,
            "system_prompt": req.system_prompt or req.messages[0].content if req.messages and req.messages[0].role == "system" else None,
        },
    )
