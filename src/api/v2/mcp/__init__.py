"""
FastBlog MCP AI Agent API v2

Uses langgraph (langchain-community) for stateful ReAct agent execution.
Endpoints:
  POST /api/v2/mcp/chat           — Non-streaming chat
  POST /api/v2/mcp/chat/stream    — SSE streaming via astream_events
  POST /api/v2/mcp/chat/{id}/resume — Resume (send new user message)
  GET  /api/v2/mcp/tools          — List tools
  GET  /api/v2/mcp/info           — Server info
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.mcp.lang import (
    stream_agent,
    run_agent,
    make_config,
)
from src.mcp.lang.llm import FastBlogLLM
from src.mcp.server import mcp_server

logger = logging.getLogger('mcp_proxy')
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
    message: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


# ─── Helper ──────────────────────────────────────────────────────

def _chat_messages_to_dicts(messages: List[ChatMessage]) -> List[Dict]:
    """Convert ChatMessage pydantic list to plain dict list."""
    result = []
    for m in messages:
        d = {"role": m.role}
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


def _system_prompt(req: ChatRequest) -> str:
    """Extract effective system prompt from request."""
    sp = req.system_prompt
    if not sp and req.messages and req.messages[0].role == "system":
        sp = req.messages[0].content or ""
    return sp or "You are a helpful AI assistant."


# ─── Non-streaming chat ──────────────────────────────────────────

@router.post("/chat")
async def chat_non_stream(req: ChatRequest):
    """Non-streaming chat — runs agent to completion."""
    conv_id = req.conversation_id or uuid.uuid4().hex[:12]
    messages = _chat_messages_to_dicts(req.messages)

    try:
        result = await run_agent(
            endpoint=req.endpoint,
            api_key=req.api_key,
            model=req.model,
            messages=messages,
            system_prompt=_system_prompt(req),
            thread_id=conv_id,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )

        msgs = result.get("messages", [])
        if msgs and hasattr(msgs[-1], "content"):
            content = msgs[-1].content or ""
            tool_calls = getattr(msgs[-1], "tool_calls", None)
        else:
            content = ""
            tool_calls = None

        return ChatResponse(
            success=True,
            conversation_id=conv_id,
            content=content,
            tool_calls=[{
                "id": tc.get("id"),
                "type": "function",
                "function": {"name": tc.get("name"), "arguments": json.dumps(tc.get("args", {}))},
            } for tc in (tool_calls or [])] if tool_calls else None,
        )
    except Exception as e:
        logger.exception("Chat non-stream error")
        raise HTTPException(status_code=500, detail=str(e))


# ─── SSE streaming chat ──────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming — yields tokens and state updates."""
    conv_id = req.conversation_id or uuid.uuid4().hex[:12]
    messages = _chat_messages_to_dicts(req.messages)
    system_prompt = _system_prompt(req)

    async def event_generator():
        accumulated = ""
        try:
            async for event in stream_agent(
                endpoint=req.endpoint,
                api_key=req.api_key,
                model=req.model,
                messages=messages,
                system_prompt=system_prompt,
                thread_id=conv_id,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            ):
                if event["type"] == "token":
                    accumulated += event["content"]
                    yield f"data: {json.dumps({'type': 'token', 'content': event['content']}, ensure_ascii=False)}\n\n"
                elif event["type"] == "done":
                    yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id, 'content': accumulated}, ensure_ascii=False)}\n\n"
                elif event["type"] == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': event['message']}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("SSE streaming error")
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


# ─── Resume chat (non-streaming, just for compatibility) ─────────

@router.post("/chat/{conv_id}/resume")
async def resume_conversation(conv_id: str, req: ChatRequest):
    """Resume — creates a new conversation with same config + history."""
    messages = _chat_messages_to_dicts(req.messages)
    last_user = messages[-1]["content"] if messages else ""

    try:
        result = await run_agent(
            endpoint=req.endpoint,
            api_key=req.api_key,
            model=req.model,
            messages=messages,
            system_prompt=_system_prompt(req),
            thread_id=conv_id,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        msgs = result.get("messages", [])
        content = msgs[-1].content if msgs and hasattr(msgs[-1], "content") else ""
        return ChatResponse(success=True, conversation_id=conv_id, content=content)
    except Exception as e:
        logger.exception("Resume error")
        raise HTTPException(status_code=500, detail=str(e))


# ─── MCP info ────────────────────────────────────────────────────

@router.get("/tools")
async def list_mcp_tools():
    """List MCP tools in OpenAI function-calling format."""
    return {"success": True, "data": mcp_server.get_openai_tools()}


@router.get("/info")
async def mcp_proxy_info():
    """Get proxy info."""
    info = mcp_server.get_server_info()
    info["backend"] = "langgraph"
    info["llm_backend"] = FastBlogLLM.__name__
    return {"success": True, "data": info}
