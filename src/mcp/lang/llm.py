"""
Custom LangChain LLM that calls any OpenAI-compatible endpoint.

Reads endpoint/api_key/model from RunnableConfig["configurable"],
so different requests can use different providers without recompiling.
"""

import json
import logging
from typing import Any, Dict, Iterator, List, Optional, cast

import httpx
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

logger = logging.getLogger('mcp.lang.llm')

# ─── Config key ─────────────────────────────────────────────────────
# Values injected via RunnableConfig["configurable"]
CFG_ENDPOINT = "llm_endpoint"
CFG_API_KEY  = "llm_api_key"
CFG_MODEL    = "llm_model"
CFG_MAX_TOKENS = "llm_max_tokens"
CFG_TEMPERATURE = "llm_temperature"


def _msg_to_dict(msg: BaseMessage) -> Dict[str, Any]:
    """Convert a LangChain message to an OpenAI-API dict."""
    d: Dict[str, Any] = {"role": msg.type}
    content = msg.content
    if msg.type in ("human", "tool"):
        d["content"] = (content or "") if isinstance(content, str) else (content or "")
    else:
        d["content"] = content if isinstance(content, str) else str(content) if content else None

    if isinstance(msg, AIMessage) and msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])},
            }
            for tc in msg.tool_calls
        ]
    if isinstance(msg, ToolMessage):
        d["tool_call_id"] = msg.tool_call_id
        d["name"] = msg.name
    return d


class FastBlogLLM(BaseChatModel):
    """
    LangChain chat model that proxies to any OpenAI-compatible API.

    Config keys (passed via RunnableConfig["configurable"]):
      llm_endpoint   — base URL, e.g. "https://api.openai.com/v1"
      llm_api_key    — API key
      llm_model      — model name, e.g. "gpt-4o-mini"
      llm_max_tokens — max tokens (default 4096)
      llm_temperature — temperature (default 0.7)
    """

    model_config = {"arbitrary_types_allowed": True}

    def bind_tools(self, tools: List[Any], **kwargs: Any) -> 'FastBlogLLM':
        """Bind tools for OpenAI-compatible tool-calling."""
        from langchain_core.tools import BaseTool
        formatted = []
        for t in tools:
            if isinstance(t, BaseTool):
                schema = t.get_input_schema().model_json_schema()
                formatted.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": schema,
                    },
                })
            elif isinstance(t, dict):
                formatted.append(t)
        return self.bind(tools=formatted, **kwargs)

    def _get_config(self, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        configurable = (config or {}).get("configurable", {}) or {}
        return {
            "endpoint": configurable.get(CFG_ENDPOINT, "https://api.openai.com/v1"),
            "api_key": configurable.get(CFG_API_KEY, ""),
            "model": configurable.get(CFG_MODEL, "gpt-4o-mini"),
            "max_tokens": configurable.get(CFG_MAX_TOKENS, 4096),
            "temperature": configurable.get(CFG_TEMPERATURE, 0.7),
        }

    @property
    def _llm_type(self) -> str:
        return "fastblog-llm"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Synchronous call — not used, we override _agenerate."""
        raise NotImplementedError("Use async invocation (ainvoke / astream)")

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        cfg = self._get_config(run_manager) if run_manager else self._get_config()

        body = {
            "model": cfg["model"],
            "messages": [_msg_to_dict(m) for m in messages],
            "max_tokens": cfg["max_tokens"],
            "temperature": cfg["temperature"],
        }
        # Pass bound tools if any
        bound_tools = getattr(self, 'tools', None) or kwargs.get('tools')
        if not bound_tools:
            bound_tools = getattr(self, '_bound_tools', None) or kwargs.get('tools')
        if bound_tools:
            body["tools"] = bound_tools
        if stop:
            body["stop"] = stop

        headers = {"Content-Type": "application/json"}
        if cfg['api_key']:
            headers["Authorization"] = f"Bearer {cfg['api_key']}"
        url = f"{cfg['endpoint'].rstrip('/')}/chat/completions"

        logger.info(f"LLM call: model={cfg['model']} msg_count={len(messages)} url={url}")

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code != 200:
                logger.error(f"LLM error {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        msg_data = choice.get("message", {})

        content = msg_data.get("content") or ""
        tool_calls_raw = msg_data.get("tool_calls")

        kwargs: Dict[str, Any] = {}
        if tool_calls_raw:
            kwargs["tool_calls"] = [
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": json.loads(tc["function"]["arguments"]),
                }
                for tc in tool_calls_raw
            ]

        ai_msg = AIMessage(content=content, **kwargs)
        gen = ChatGeneration(message=ai_msg)
        return ChatResult(generations=[gen])

    # Streaming support — optional but adds real-time UX
    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream tokens from the LLM (used by langgraph for real-time output)."""
        from langchain_core.outputs import ChatGenerationChunk

        cfg = self._get_config(run_manager) if run_manager else self._get_config()

        body = {
            "model": cfg["model"],
            "messages": [_msg_to_dict(m) for m in messages],
            "max_tokens": cfg["max_tokens"],
            "temperature": cfg["temperature"],
            "stream": True,
        }
        headers = {"Content-Type": "application/json"}
        if cfg['api_key']:
            headers["Authorization"] = f"Bearer {cfg['api_key']}"
        url = f"{cfg['endpoint'].rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", url, json=body, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        yield ChatGenerationChunk(message=AIMessage(content=delta["content"]))
                    if delta.get("tool_calls"):
                        # Simplified — full tool-call streaming is complex
                        pass
