"""出站 HTTP 的 SSRF 兜底：**每一次**请求（含重定向的每一跳）都过同一套校验。

## 为什么需要这个模块

`validate_outbound_url` 只能校验**初始** URL。客户端一旦带 `follow_redirects=True`，
目标只要 302 到 `169.254.169.254` 或内网地址，校验就被整个绕过去了 ——
"校验了首跳"不等于"校验了实际访问的地址"。

httpx 的 `request` 事件钩子在**每次真正发出请求之前**执行（重定向产生的下一跳
也算一次请求），在这里抛异常即可中止，因此校验点与实际出站目标是同一集合。
异常继承 `httpx.HTTPError`，调用方现成的 `except httpx.HTTPError` 能直接兜住。
"""

from __future__ import annotations

from typing import Any

import httpx

from src.utils.security.safe import validate_outbound_url


class OutboundBlockedError(httpx.HTTPError):
    """出站目标未通过校验（内网 / 链路本地 / 云元数据 / 非 http(s)）"""


def _assert_outbound_allowed(request: httpx.Request) -> None:
    ok, error = validate_outbound_url(str(request.url))
    if not ok:
        raise OutboundBlockedError(f"出站请求被拦截：{error}")


def _with_guard(kwargs: dict[str, Any]) -> dict[str, Any]:
    hooks = dict(kwargs.pop("event_hooks", {}) or {})
    hooks["request"] = [*hooks.get("request", []), _assert_outbound_allowed]
    kwargs.setdefault("follow_redirects", True)
    return {**kwargs, "event_hooks": hooks}


def guarded_async_client(**kwargs: Any) -> httpx.AsyncClient:
    """带逐跳校验的 `httpx.AsyncClient`（参数透传）"""
    return httpx.AsyncClient(**_with_guard(kwargs))


def guarded_client(**kwargs: Any) -> httpx.Client:
    """带逐跳校验的同步 `httpx.Client`"""
    return httpx.Client(**_with_guard(kwargs))


def guarded_get(url: str, **kwargs: Any) -> httpx.Response:
    """`httpx.get` 的安全替代：首跳同样会被校验"""
    with guarded_client(**kwargs) as client:
        return client.get(url)
