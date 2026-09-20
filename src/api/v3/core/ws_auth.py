"""WebSocket 鉴权：Cookie → 子协议 → query 三级回退

浏览器 WebSocket API **无法自定义请求头**，所以不能沿用 ``Authorization: Bearer``；
这里按优先级回退，并把"解析不出身份"一律表示为 ``None``（调用方据此以 4401 关闭连接，
而不是"连上了但没权限"）。

> 从 ``content/collaboration/controller.py`` 提取（2026-09-20 批次 17）：
> yjs 协同与群聊消息两个 WS 端点共用同一套准入逻辑，避免两份实现各自演化。
"""

from typing import Optional

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from src.api.v3.core.exceptions import UnauthorizedError
from src.api.v3.core.security import decode_token


def extract_ws_token(websocket: WebSocket) -> Optional[str]:
    """Cookie ``access_token`` → 子协议 ``bearer.<token>`` → query ``token``

    query 会进访问日志，因此排最后（最次选）。
    """
    token = websocket.cookies.get("access_token") or websocket.cookies.get("access_token_cookie")
    if token:
        return token
    protocols = websocket.headers.get("sec-websocket-protocol") or ""
    for item in (part.strip() for part in protocols.split(",")):
        if item.startswith("bearer."):
            return item[len("bearer."):]
    return websocket.query_params.get("token")


async def resolve_ws_user(db: AsyncSession, websocket: WebSocket) -> Optional[User]:
    """解析 WS 连接的身份；任何一步失败都返回 ``None``（调用方据此关闭连接）"""
    token = extract_ws_token(websocket)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except UnauthorizedError:
        return None
    subject = str(payload.get("sub") or "")
    if not subject:
        return None
    user: Optional[User] = None
    if subject.isdigit():
        user = await db.get(User, int(subject))
    if user is None:
        user = (await db.execute(select(User).where(User.username == subject))).scalars().first()
    if user is None or not bool(getattr(user, "is_active", True)):
        return None
    return user
