"""
FastBlog MCP AI Agent API v2 — uses src.mcp.agent for clean direct execution.
Endpoints:
  POST /api/v2/mcp/chat        — Non-streaming chat
  POST /api/v2/mcp/chat/stream — SSE streaming chat
  GET  /api/v2/mcp/tools       — List MCP tools
  GET  /api/v2/mcp/info        — Server info
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.mcp.agent import LLMConfig, run_agent, stream_agent
from src.mcp.server import mcp_server

logger = logging.getLogger("mcp_proxy")
router = APIRouter(prefix="/mcp", tags=["MCP AI Agent"])


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
    content: Optional[str] = None
    message: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────

def _to_cfg(req: ChatRequest) -> LLMConfig:
    sp = req.system_prompt
    if not sp and req.messages and req.messages[0].role == "system":
        sp = req.messages[0].content or ""
    return LLMConfig(
        endpoint=req.endpoint,
        api_key=req.api_key,
        model=req.model,
        system_prompt=sp or "You are a helpful AI assistant.",
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )


def _to_dicts(messages: List[ChatMessage]) -> List[Dict]:
    """Convert pydantic ChatMessage list to plain dicts."""
    result = []
    for m in messages:
        d: Dict[str, Any] = {"role": m.role}
        if m.content is not None:
            d["content"] = m.content
        if m.tool_calls:
            d["tool_calls"] = m.tool_calls
        if m.tool_call_id:
            d["tool_call_id"] = m.tool_call_id
        if m.name:
            d["name"] = m.name
        result.append(d)
    return result


# ─── Non-streaming chat ──────────────────────────────────────────

@router.post("/chat")
async def chat_non_stream(req: ChatRequest):
    """Non-streaming chat."""
    conv_id = req.conversation_id or uuid.uuid4().hex[:12]
    cfg = _to_cfg(req)
    messages = _to_dicts(req.messages)

    try:
        state = await run_agent(cfg, messages, conversation_id=conv_id)

        last = state.messages[-1] if state.messages else {}
        content = last.get("content", "") if last.get("role") == "assistant" else ""

        return ChatResponse(
            success=not state.errors,
            conversation_id=conv_id,
            content=content,
            message=state.errors[-1] if state.errors else None,
        )
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))


# ─── SSE streaming chat ──────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming chat."""
    conv_id = req.conversation_id or uuid.uuid4().hex[:12]
    cfg = _to_cfg(req)
    messages = _to_dicts(req.messages)

    async def event_generator():
        try:
            async for event in stream_agent(cfg, messages, conversation_id=conv_id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("SSE error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Info ─────────────────────────────────────────────────────────

@router.get("/tools")
async def list_mcp_tools():
    return {"success": True, "data": mcp_server.get_openai_tools()}


@router.get("/info")
async def mcp_proxy_info():
    info = mcp_server.get_server_info()
    info["backend"] = "mcp.agent"
    return {"success": True, "data": info}
