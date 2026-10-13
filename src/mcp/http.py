"""MCP over HTTP —— 单一 POST 端点（Streamable HTTP 风格）。

挂载路径：``POST /api/v3/mcp``，请求体是 JSON-RPC 2.0，响应也是 JSON-RPC 2.0。

**认证与授权完全复用平台既有链路**，不另建一套：

    get_current_user（JWT 或 ``X-API-Key``）→ ``load_codes`` 取**真实三段权限码**
    → 身份若来自 API Token，再与令牌 ``scopes`` 求交（同 REST 的 ``AuthControl``）
    → 注入 ``UserCtx``

因此 MCP 的权限**不可能高于**同一账号在 REST 上的权限；用户被降权时，令牌同步失效。

未认证请求由 ``CurrentUser`` 依赖直接 401 —— 这里是"要认证"，而不是"连不上"。
"""

from __future__ import annotations

from typing import Any, FrozenSet, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from src.api.v3.core.deps import CurrentUser, DBSession
from src.api.v3.core.permission.loader import load_codes
from src.auth.api_token import Principal
from src.mcp._context import UserCtx, set_user_ctx
from src.mcp.server import mcp_server

router = APIRouter(tags=["MCP"])


def _token_scopes(request: Request) -> Optional[FrozenSet[str]]:
    """本次请求若通过 API Token 认证，取出它的 scopes（否则 ``None`` = 用户会话）"""
    principal = getattr(getattr(request, "state", None), "principal", None)
    if isinstance(principal, Principal):
        return principal.scopes
    return None


async def _inject_user_ctx(request: Request, db: Any, current_user: Any) -> UserCtx:
    """把当前身份（含**真实权限码**）注入 MCP 上下文"""
    codes = await load_codes(db, current_user.id, request=request)
    is_superuser = bool(getattr(current_user, "is_superuser", False))
    ctx = UserCtx(
        id=current_user.id,
        username=str(getattr(current_user, "username", "") or current_user.id),
        is_superuser=is_superuser,
        role="superuser" if is_superuser else "user",
        permission_codes=frozenset(codes),
        token_scopes=_token_scopes(request),
    )
    set_user_ctx(ctx)
    return ctx


@router.post("/mcp", summary="MCP（Model Context Protocol）JSON-RPC 端点")
async def mcp_endpoint(
    request: Request,
    payload: dict,
    db: DBSession,
    current_user: CurrentUser,
) -> Response:
    """接入任何支持 MCP 的客户端（Claude Desktop / Cursor / 自研 agent）。

    请求体示例（握手）::

        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "clientInfo": {"name": "cursor"}}}

    通知类消息（``notifications/initialized`` 等）按规范返回 **202 无内容**。
    """
    await _inject_user_ctx(request, db, current_user)
    try:
        result = await mcp_server.handle_request(payload)
    finally:
        # 上下文是 contextvar，用完必须清掉，避免泄漏到同进程的下一个请求
        set_user_ctx(None)

    if result is None:
        return Response(status_code=202)
    return JSONResponse(result)


__all__ = ["router"]
