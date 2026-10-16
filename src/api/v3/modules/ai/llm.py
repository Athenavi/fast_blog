"""调用大模型：**OpenAI 兼容**与 **Anthropic** 两套协议（真实 HTTP，不 mock）

支持范围与"用户自定义连接"的落点：

  - 协议由 ``provider`` 决定（见 :data:`PROVIDER_PROTOCOLS`）：``openai`` 系（含 deepseek /
    qwen / moonshot / ollama / azure 等一切 OpenAI 兼容端点）走 ``/chat/completions``；
    ``anthropic``（claude）走 ``/v1/messages``；
  - **端点可自定义**：``api_url`` 是 base_url（如 ``https://api.deepseek.com/v1``、
    自建网关、内网 vLLM），末尾若已带完整路径则原样使用；
  - **模型名可自定义**；``api_version`` 对 Anthropic 是 ``anthropic-version`` 头，
    对 OpenAI 系作为 ``api-version`` query（Azure 用）；``extra_headers`` 可补任意头
    （Azure 的 ``api-key``、自建网关的鉴权头等）；
  - ``api_key`` 允许为空（本地 Ollama 之类不需要鉴权），此时不发鉴权头。

两套协议的请求/响应差异都收敛在 :func:`complete` 返回的 :class:`LLMResult` 里，
上层（``ai/workflow`` 执行引擎、``ai/config`` 的连接测试）不用关心协议细节。
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from src.api.v3.core.exceptions import BadRequestError

#: LLM 调用超时（秒）——生成类接口比普通 API 慢得多
LLM_TIMEOUT = 120.0

#: provider → 协议。未知 provider 按 OpenAI 兼容处理（自建网关绝大多数都是这个格式）
PROVIDER_PROTOCOLS: dict[str, str] = {
    "openai": "openai",
    "azure": "openai",
    "azure_openai": "openai",
    "deepseek": "openai",
    "qwen": "openai",
    "moonshot": "openai",
    "zhipu": "openai",
    "ollama": "openai",
    "vllm": "openai",
    "custom": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
}

ANTHROPIC_DEFAULT_VERSION = "2023-06-01"


@dataclass
class LLMSettings:
    """一次调用需要的连接信息（由调用方从 AIConfig + 解密后的密钥组装）"""

    provider: str
    api_url: str
    api_key: str = ""
    model: str = ""
    api_version: Optional[str] = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    max_tokens: int = 1024


@dataclass
class LLMResult:
    """统一结果（两套协议的差异都在这里抹平）"""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    protocol: str = "openai"
    raw: dict[str, Any] = field(default_factory=dict)


def protocol_for(provider: str) -> str:
    """provider → 协议（未知按 openai 兼容）"""
    return PROVIDER_PROTOCOLS.get((provider or "").strip().lower(), "openai")


def _endpoint(base_url: str, path: str) -> str:
    """把 base_url 与协议路径拼起来（base 已带完整路径则原样用）"""
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise BadRequestError("未配置 API 端点（api_url）")
    if base.endswith(path):
        return base
    return f"{base}{path}"


def _headers_for(settings: LLMSettings, protocol: str) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.api_key:
        if protocol == "anthropic":
            headers["x-api-key"] = settings.api_key
            headers["anthropic-version"] = settings.api_version or ANTHROPIC_DEFAULT_VERSION
        else:
            headers["Authorization"] = f"Bearer {settings.api_key}"
    # 自定义头最后合并（可覆盖上面的默认值，例如 Azure 用 api-key）
    headers.update({str(k): str(v) for k, v in (settings.extra_headers or {}).items()})
    return headers


def _error_message(payload: Any, fallback: str) -> str:
    """从厂商错误体里挖出人话（openai / anthropic 都是 {error: {message}}）"""
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(error, str) and error:
            return error
    return fallback


async def _post(url: str, body: dict, headers: dict, params: Optional[dict] = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            resp = await client.post(url, json=body, headers=headers, params=params or {})
    except httpx.HTTPError as exc:
        raise BadRequestError(f"调用大模型失败（{url}）：{exc}") from exc

    try:
        payload = resp.json()
    except ValueError as exc:
        raise BadRequestError(
            f"大模型返回了非 JSON 响应（HTTP {resp.status_code}）：{(resp.text or '')[:200]}"
        ) from exc

    if resp.status_code >= 400:
        raise BadRequestError(
            f"大模型拒绝请求（HTTP {resp.status_code}）："
            f"{_error_message(payload, (resp.text or '')[:200])}"
        )
    if not isinstance(payload, dict):
        raise BadRequestError(f"大模型返回了意外结构（HTTP {resp.status_code}）")
    return payload


async def _call_openai(
    settings: LLMSettings, *, system: Optional[str], prompt: str, max_tokens: int, temperature: Optional[float]
) -> LLMResult:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body: dict[str, Any] = {
        "model": settings.model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        body["temperature"] = temperature

    # api_version 对 OpenAI 系走 query（Azure OpenAI 的形状）
    params = {"api-version": settings.api_version} if settings.api_version else None
    payload = await _post(
        _endpoint(settings.api_url, "/chat/completions"),
        body,
        _headers_for(settings, "openai"),
        params,
    )

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise BadRequestError("OpenAI 兼容响应缺少 choices")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    text = message.get("content")
    if text is None:
        # 某些网关把内容放在 text 字段
        text = first.get("text")
    if text is None:
        raise BadRequestError("OpenAI 兼容响应里没有可用的回复内容")

    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return LLMResult(
        text=str(text),
        model=str(payload.get("model") or settings.model),
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        protocol="openai",
        raw=payload,
    )


async def _call_anthropic(
    settings: LLMSettings, *, system: Optional[str], prompt: str, max_tokens: int, temperature: Optional[float]
) -> LLMResult:
    body: dict[str, Any] = {
        "model": settings.model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    # Anthropic 把系统提示词放在顶层 system，而不是 messages 里
    if system:
        body["system"] = system
    if temperature is not None:
        body["temperature"] = temperature

    payload = await _post(
        _endpoint(settings.api_url, "/v1/messages"),
        body,
        _headers_for(settings, "anthropic"),
    )

    blocks = payload.get("content")
    if not isinstance(blocks, list):
        raise BadRequestError("Anthropic 响应缺少 content 数组")
    text = "".join(
        str(block.get("text") or "")
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    )
    if not text:
        raise BadRequestError("Anthropic 响应里没有可用的文本内容")

    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return LLMResult(
        text=text,
        model=str(payload.get("model") or settings.model),
        prompt_tokens=int(usage.get("input_tokens") or 0),
        completion_tokens=int(usage.get("output_tokens") or 0),
        protocol="anthropic",
        raw=payload,
    )


async def complete(
    settings: LLMSettings,
    *,
    prompt: str,
    system: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> LLMResult:
    """按 provider 选协议真实调用一次（失败一律抛 ``BadRequestError`` 并带上厂商原因）"""
    if not (prompt or "").strip():
        raise BadRequestError("提示词（prompt）不能为空")
    if not (settings.model or "").strip():
        raise BadRequestError("未配置模型名（model）")

    protocol = protocol_for(settings.provider)
    tokens = int(max_tokens or settings.max_tokens or 1024)
    if protocol == "anthropic":
        return await _call_anthropic(
            settings, system=system, prompt=prompt, max_tokens=tokens, temperature=temperature
        )
    return await _call_openai(
        settings, system=system, prompt=prompt, max_tokens=tokens, temperature=temperature
    )
