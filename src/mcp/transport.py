"""MCP 的 stdio 传输：``python -m src.mcp`` 逐行读写 JSON-RPC。

本地 MCP 客户端（Claude Desktop / Cursor 等）以**子进程**方式接入时用的就是这个：

    FASTBLOG_MCP_TOKEN=fbk_xxx python -m src.mcp

**认证**：从环境变量 ``FASTBLOG_MCP_TOKEN`` 读取一个 **API Token**
（``fbk_<prefix>_<secret>``，在后台「API 令牌」页签发），走与 HTTP 完全相同的校验：
Argon2 哈希比对 + 是否启用 + 是否过期 → 用户 → ``load_codes`` 取真实权限码
→ 与令牌 ``scopes`` 求交。

**未配置令牌时不会假装成功**：上下文为空，任何工具调用都会如实返回「未登录」。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, FrozenSet, Optional

from shared.models import User as UserModel
from src.api.v3.core.permission.loader import load_codes
from src.auth.api_token import authenticate_api_key, principal_from_token
from src.mcp._context import UserCtx, set_user_ctx
from src.mcp.server import mcp_server
from src.utils.database.unified_manager import db_manager

#: 存放 API Token 的环境变量名
TOKEN_ENV = "FASTBLOG_MCP_TOKEN"

#: JSON-RPC 标准错误码
PARSE_ERROR = -32700
INVALID_REQUEST = -32600


def _log(message: str) -> None:
    """日志一律走 stderr —— stdout 被 JSON-RPC 独占，混入日志会破坏协议"""
    print(f"[mcp] {message}", file=sys.stderr, flush=True)


async def build_stdio_ctx() -> Optional[UserCtx]:
    """用 ``FASTBLOG_MCP_TOKEN`` 构造上下文；没有令牌或校验失败返回 ``None``"""
    raw = (os.environ.get(TOKEN_ENV) or "").strip()
    if not raw:
        _log(f"未设置 {TOKEN_ENV}：将以「未认证」身份运行，所有工具都会返回未登录")
        return None

    async with db_manager.get_session() as db:
        row = await authenticate_api_key(db, raw)
        if row is None:
            _log(f"{TOKEN_ENV} 校验失败（不存在 / 已撤销 / 已过期）")
            return None

        user = await db.get(UserModel, row.user_id)
        if user is None:
            _log(f"令牌指向的用户不存在：user_id={row.user_id}")
            return None

        principal = principal_from_token(row, user)
        codes = await load_codes(db, user.id)
        scopes: Optional[FrozenSet[str]] = principal.scopes
        _log(
            f"已认证 user={getattr(user, 'username', user.id)} "
            f"权限码={len(codes)} 令牌 scopes={'全部' if scopes is None else len(scopes)}"
        )
        return UserCtx(
            id=user.id,
            username=str(getattr(user, "username", "") or user.id),
            is_superuser=bool(getattr(user, "is_superuser", False)),
            role="superuser" if getattr(user, "is_superuser", False) else "user",
            permission_codes=frozenset(codes),
            token_scopes=scopes,
        )


async def handle_line(line: str, ctx: Optional[UserCtx]) -> Optional[str]:
    """处理一行输入，返回应写到 stdout 的内容（``None`` = 无需响应，如通知）。

    单独抽出来是为了可测：HTTP 端点的行为与它保持一致（同一 ``handle_request``）。
    """
    try:
        payload: Any = json.loads(line)
    except json.JSONDecodeError as exc:
        return json.dumps(
            {"jsonrpc": "2.0", "id": None, "error": {"code": PARSE_ERROR, "message": f"解析失败: {exc.msg}"}},
            ensure_ascii=False,
        )

    if not isinstance(payload, dict):
        return json.dumps(
            {"jsonrpc": "2.0", "id": None, "error": {"code": INVALID_REQUEST, "message": "请求体必须是 JSON 对象"}},
            ensure_ascii=False,
        )

    set_user_ctx(ctx)
    try:
        result = await mcp_server.handle_request(payload)
    except Exception as exc:  # noqa: BLE001 - 单行失败不应让整个会话退出
        _log(f"处理请求失败：{exc}")
        return json.dumps(
            {"jsonrpc": "2.0", "id": payload.get("id"), "error": {"code": -32603, "message": "内部错误"}},
            ensure_ascii=False,
        )
    finally:
        set_user_ctx(None)

    if result is None:
        return None
    return json.dumps(result, ensure_ascii=False)


async def serve_stdio() -> int:
    """stdio 主循环：逐行读 stdin → 处理 → 写 stdout"""
    ctx = await build_stdio_ctx()
    _log(f"stdio 会话就绪：{mcp_server.get_server_info()}")
    loop = asyncio.get_running_loop()

    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:  # EOF：客户端关闭
            break
        line = line.strip()
        if not line:
            continue

        response = await handle_line(line, ctx)
        if response is not None:
            sys.stdout.write(response + "\n")
            sys.stdout.flush()

    _log("stdin 已关闭，退出")
    return 0


__all__ = ["TOKEN_ENV", "build_stdio_ctx", "handle_line", "serve_stdio"]
