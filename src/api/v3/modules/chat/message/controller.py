"""chat.message 模块路由（批次 17）：群聊消息 + WebSocket 实时通道。

::

    GET    /api/v3/chat/message/my-groups          我加入的群聊（登录；前台聊天页左栏）
    GET    /api/v3/chat/message/{group_id}           群内消息（登录 + 群成员；分页，时间正序）
    POST   /api/v3/chat/message                      发送消息（登录 + 群成员；落库 + Redis 广播）
    DELETE /api/v3/chat/message/item/{message_id}    撤回本人消息（登录；软删除 + 广播 recall）
    WS     /api/v3/chat/message/ws/{group_id}        实时通道

访问控制：**仅需登录**（前端用户接口，不发权限码）。

  - HTTP 写端点登记在 ``src/api/v3/core/permission/audit.py`` 的 ``EXEMPT_WRITE_ENDPOINTS``；
  - WebSocket 路由没有 ``methods``，**启动期权限审计会跳过它**，因此准入逻辑必须写在
    路由体内（``chat_websocket`` 里）：「解析不出身份 → 4401 关闭」「非群成员 → 4403 关闭」。
    鉴权复用了 ``src/api/v3/core/ws_auth.py`` 的 ``resolve_ws_user``，不自行实现；
    **拒绝时必须先 accept 再 close**（``accept_then_close``）：未 accept 就 close 会让
    uvicorn 直接 403 拒绝握手，浏览器只看得到 1006，拿不到 4401/4403。
"""

import json
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession
from src.api.v3.core.logger import get_logger
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.core.ws_auth import (
    WS_CLOSE_FORBIDDEN,
    WS_CLOSE_UNAUTHORIZED,
    accept_then_close,
    resolve_ws_user,
)
from src.api.v3.modules.chat.message.schema import ChatMessageCreate
from src.api.v3.modules.chat.message.service import chat_message_service, group_broadcaster

logger = get_logger("chat.message")

router = APIRouter(prefix="/message", tags=["chat-message"], route_class=OperationLogRoute)


@router.get("/my-groups", response_model=ResponseModel, summary="我加入的群聊")
async def my_groups(db: DBSession, current: CurrentUser) -> dict:
    """前台聊天页左栏：只列**本人加入**的群（不需要 group:view 管理权限）"""
    return resp.success(await chat_message_service.my_groups(db, current.id))


@router.get("/{group_id}", response_model=ResponseModel, summary="群内消息（分页，时间正序）")
async def list_messages(
    group_id: int,
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """仅登录 + 必须是该群成员；后端取最新 N 条后按时间升序返回，含已撤回消息。"""
    items, total = await chat_message_service.list_messages(
        db, group_id, current.id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="发送群聊消息")
async def send_message(
    payload: ChatMessageCreate, db: DBSession, current: CurrentUser
) -> dict:
    """落库 + 更新群的 ``last_message_at`` + 通过 Redis 广播给 ``chat:group:{group_id}``。"""
    return resp.success(
        await chat_message_service.create_message(db, current.id, payload), msg="已发送"
    )


@router.delete("/item/{message_id}", response_model=ResponseModel, summary="撤回本人消息")
async def recall_message(message_id: int, db: DBSession, current: CurrentUser) -> dict:
    """只能撤回本人发送的消息（否则 403）；软删除并广播一条 recall 事件。"""
    await chat_message_service.recall_message(db, current.id, message_id)
    return resp.success(None, msg="已撤回")


@router.websocket("/ws/{group_id}")
async def chat_websocket(websocket: WebSocket, group_id: int, db: DBSession) -> None:
    """群聊实时通道。

    准入（**必须写在路由体内**：WS 路由没有 methods，启动期权限审计会跳过）：
      - 解析不出身份 → ``4401`` 关闭后 return；
      - 非该群成员（含群不存在）→ ``4403`` 关闭后 return。

    准入失败**先 accept 再 close**（``accept_then_close``）：未 accept 就 close 会被
    uvicorn 当成拒绝握手（HTTP 403），浏览器侧只能看到 ``1006``。

    ``accept`` 之后订阅 ``chat:group:{group_id}`` 频道，把收到的 JSON 转发给本连接；
    循环读文本帧仅用于忽略心跳（客户端可发 ``{"type":"ping"}``，服务端回 ``pong``）；
    断开时在 ``finally`` 清理订阅。
    """
    user = await resolve_ws_user(db, websocket)
    if user is None:
        await accept_then_close(websocket, WS_CLOSE_UNAUTHORIZED, "unauthorized")
        return
    if not await chat_message_service.is_member(db, group_id, user.id):
        await accept_then_close(websocket, WS_CLOSE_FORBIDDEN, "not a member")
        return

    await websocket.accept()
    client_id = uuid.uuid4().hex[:12]
    await group_broadcaster.subscribe(group_id, client_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            if not raw:
                continue
            try:
                envelope = json.loads(raw)
            except (ValueError, TypeError):
                continue  # 非 JSON 帧一律忽略
            if isinstance(envelope, dict) and envelope.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - 单连接异常不应影响其它连接
        logger.exception("群聊 WS 连接异常: group_id=%s client=%s", group_id, client_id)
    finally:
        await group_broadcaster.unsubscribe(group_id, client_id)
