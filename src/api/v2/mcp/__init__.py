"""
FastBlog MCP Chat Proxy API v2

AI 对话代理 — 接收用户配置的 LLM 端点和 API Key，转发请求并执行 MCP 工具
不存储任何 LLM 凭据（凭据仅在前端 localStorage 中）
"""

import json
import logging
from typing import Any, List, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.mcp.server import mcp_server

logger = logging.getLogger('mcp_proxy')
router = APIRouter(prefix="/mcp", tags=["MCP Chat Proxy"])


# ─── 请求/响应模型 ─────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # system | user | assistant | tool
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class ChatRequest(BaseModel):
    endpoint: str  # LLM API 地址，如 https://api.openai.com/v1
    api_key: str   # API Key
    model: str     # 模型名，如 gpt-4o, deepseek-chat, claude-3-opus
    messages: List[ChatMessage]
    max_tokens: int = 4096
    temperature: float = 0.7


class ChatResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


# ─── 代理端点 ──────────────────────────────────────────

@router.post("/chat/completions")
async def chat_completions(req: ChatRequest):
    """
    AI 对话代理
    
    将用户消息转发到用户指定的 LLM 端点，同时注入 MCP 工具定义。
    当 LLM 调用工具时，由服务器端执行并将结果返回给 LLM。
    
    工作流程:
    1. 首次调用：发送消息 + MCP 工具定义给 LLM
    2. 如 LLM 返回 tool_calls → 执行工具 → 发送结果给 LLM
    3. 重复直到 LLM 返回纯文本响应
    """
    try:
        # 构建请求体
        openai_messages = _build_openai_messages(req.messages)
        tools = mcp_server.get_openai_tools()

        # 最多 5 轮工具调用
        max_rounds = 5
        for _round in range(max_rounds):
            # 调用 LLM
            llm_response = await _call_llm(
                endpoint=req.endpoint.rstrip("/"),
                api_key=req.api_key,
                model=req.model,
                messages=openai_messages,
                tools=tools if _round == 0 else None,  # 仅首轮注入工具定义
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            )

            choice = llm_response.get("choices", [{}])[0]
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason", "")

            # 提取消息内容
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls")

            # 如果没有工具调用，返回最终结果
            if not tool_calls:
                return ChatResponse(success=True, content=content)

            # 执行工具调用
            openai_messages.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})

            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}

                tool_result = await _execute_mcp_tool(tool_name, tool_args)
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                })

        # 达到最大轮数后返回最后的消息
        return ChatResponse(success=True, content="已达到最大工具调用轮数，请简化操作")

    except httpx.HTTPStatusError as e:
        logger.error(f"LLM 调用失败: {e.response.status_code} {e.response.text[:500]}")
        raise HTTPException(status_code=502, detail=f"LLM 调用失败: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"LLM 连接失败: {e}")
        raise HTTPException(status_code=502, detail=f"无法连接到 {req.endpoint}")
    except Exception as e:
        logger.exception("MCP 代理异常")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_mcp_tools():
    """列出 MCP 工具（OpenAI function-calling 格式）"""
    return {"success": True, "data": mcp_server.get_openai_tools()}


@router.get("/info")
async def mcp_proxy_info():
    """获取 MCP 代理信息"""
    info = mcp_server.get_server_info()
    info["proxy_version"] = "1.0.0"
    return {"success": True, "data": info}


# ─── 内部函数 ──────────────────────────────────────────

def _build_openai_messages(messages: List[ChatMessage]) -> List[Dict]:
    """将我们的消息格式转为 OpenAI API 格式"""
    result = []
    for msg in messages:
        entry = {"role": msg.role}
        if msg.content is not None:
            entry["content"] = msg.content
        if msg.tool_calls:
            entry["tool_calls"] = msg.tool_calls
        if msg.tool_call_id:
            entry["tool_call_id"] = msg.tool_call_id
        if msg.name:
            entry["name"] = msg.name
        result.append(entry)
    return result


async def _call_llm(
    endpoint: str,
    api_key: str,
    model: str,
    messages: List[Dict],
    tools: Optional[List[Dict]] = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> Dict:
    """调用 LLM API（OpenAI-compatible 格式）"""
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        body["tools"] = tools

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{endpoint}/chat/completions",
            json=body,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


async def _execute_mcp_tool(name: str, arguments: Dict) -> Any:
    """执行 MCP 工具并返回结果"""
    mcp_request = {
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
        "id": "proxy-1",
    }
    response = await mcp_server.handle_request(mcp_request)
    if "error" in response:
        raise ValueError(response["error"]["message"])

    content = response.get("result", {}).get("content", [])
    if content:
        text = content[0].get("text", "{}")
        return json.loads(text)
    return {"success": True}
