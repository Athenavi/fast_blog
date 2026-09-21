"""内置适配器的公共 HTTP 助手（**真实调用**，失败一律带厂商原因抛出）

只做三件事：发请求、解析 JSON、把厂商的错误体挖成人话。
各平台的协议差异（XML-RPC / 表单 / JSON / 签名）留在各自模块里，不在这里搅成一锅。
"""

from typing import Any, Optional

import httpx

from src.api.v3.core.exceptions import BadRequestError

#: 平台调用超时（秒）
DEFAULT_TIMEOUT = 30.0


def extract_error(payload: Any, fallback: str) -> str:
    """从厂商错误体里挖出可读原因（各家字段名不同）

    先把**带错误码**的风格排在最前（``errcode``/``errmsg``、``code``/``message``）——
    码与原因一起给出才便于排查（微信的 ``errcode=40164`` 就是 IP 白名单问题）。
    """
    if isinstance(payload, dict):
        for code_key, msg_key in (
                ("errcode", "errmsg"),
                ("error_code", "error_msg"),
                ("code", "message"),
        ):
            code = payload.get(code_key)
            if code not in (None, 0, "0", "success", ""):
                message = payload.get(msg_key) or payload.get("message") or ""
                return f"{code_key}={code} {message}".strip()
        # Medium 风格：errors: [{message: ...}]
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict) and first.get("message"):
                return str(first["message"])
            if isinstance(first, str) and first:
                return first
        for key in ("error", "message", "msg", "detail"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, dict):
                inner = value.get("message") or value.get("msg")
                if inner:
                    return str(inner)
    if isinstance(payload, str) and payload.strip():
        return payload.strip()[:300]
    return fallback


async def _request(
    method: str,
    url: str,
    *,
    json_body: Optional[dict] = None,
    data: Optional[dict] = None,
    content: Optional[bytes] = None,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            return await client.request(
                method,
                url,
                json=json_body,
                data=data,
                content=content,
                headers=headers or {},
                params=params or {},
            )
    except httpx.HTTPError as exc:
        raise BadRequestError(f"请求 {url} 失败：{exc}") from exc


async def post_json(
    url: str,
    payload: dict,
    *,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """POST JSON 并解析响应（HTTP >= 400 或响应非 JSON 都如实报错）"""
    resp = await _request(
        "POST", url, json_body=payload, headers=headers, params=params, timeout=timeout
    )
    return _parse(resp, url)


async def post_form(
    url: str,
    data: dict,
    *,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """POST 表单（微博 OAuth2 的多数接口是表单风格）"""
    resp = await _request("POST", url, data=data, headers=headers, params=params, timeout=timeout)
    return _parse(resp, url)


async def post_raw(
    url: str,
    content: bytes,
    *,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> httpx.Response:
    """POST 原始字节（XML-RPC / multipart 场景自行处理响应）"""
    return await _request(
        "POST", url, content=content, headers=headers, params=params, timeout=timeout
    )


async def get_json(
    url: str,
    *,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    resp = await _request("GET", url, headers=headers, params=params, timeout=timeout)
    return _parse(resp, url)


def _parse(resp: httpx.Response, url: str) -> dict:
    try:
        payload = resp.json()
    except ValueError as exc:
        raise BadRequestError(
            f"{url} 返回了非 JSON 响应（HTTP {resp.status_code}）：{(resp.text or '')[:200]}"
        ) from exc
    if resp.status_code >= 400:
        raise BadRequestError(
            f"{url} 拒绝请求（HTTP {resp.status_code}）："
            f"{extract_error(payload, (resp.text or '')[:200])}"
        )
    if not isinstance(payload, dict):
        raise BadRequestError(f"{url} 返回了意外结构（HTTP {resp.status_code}）")
    return payload


def require(credentials: dict, key: str, message: str) -> str:
    """取凭据里的必填项（缺失就直接说清要填什么）"""
    value = str((credentials or {}).get(key) or "").strip()
    if not value:
        raise BadRequestError(message)
    return value
