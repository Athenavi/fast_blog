"""chat.message 模块业务逻辑：群聊消息落库 + Redis 实时广播（含降级）。

分层：

  - ``ChatMessageService``（单例 ``chat_message_service``）：消息列表 / 发送 / 撤回，
    是唯一的 DB 访问路径；
  - ``GroupBroadcaster``（单例 ``group_broadcaster``）：``chat:group:{group_id}``
    频道的跨进程广播，照 ``content/collaboration/yjs_service.py`` 的
    ``PUBLISH / PSUBSCRIBE + 降级告警`` 模式实现。

广播设计（与 yjs 略有不同——这里负载本身就是业务 JSON，无需 envelope）：

  1. **Redis 可用**：``broadcast`` 只做 ``PUBLISH``；每个 worker 的 ``psubscribe``
     监听器收到消息后扇出给**本进程**订阅者 —— 发布者进程同样经由监听器扇出，
     因此天然不会重复投递，也无需 ``origin`` 标识。
  2. **Redis 不可用**：降级为直接进程内扇出，并 ``logger.warning(...)`` 明确告警
     （多 worker 下，同一群的连接若落在不同进程则互相收不到消息）。

成员校验：群不存在 → 404；群存在但调用者非成员 → 403（WS 准入侧统一以 4403 关闭）。
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Optional

from fastapi import WebSocket
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.chat import ChatGroup, ChatGroupMember, ChatMessage
from shared.models.user import User as UserModel
from src.api.v3.core.exceptions import ForbiddenError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.chat.message.schema import ChatMessageCreate

logger = get_logger("chat.message")

#: Redis 频道前缀（每个群一条频道，频道名即契约 ``chat:group:{group_id}``）
CHANNEL_PREFIX = "chat:group:"


def channel_of(group_id: int) -> str:
    """群消息频道名"""
    return f"{CHANNEL_PREFIX}{group_id}"


def serialize_message(item: ChatMessage, *, username: Optional[str] = None) -> dict:
    """把一条 ``ChatMessage`` 序列化为对外字段集（列表项与 WS 广播共用）。

    撤回（``is_deleted=True``）的消息仍然返回，但 ``content`` 置空 —— 前端据此
    显示「已撤回」占位，且不会让消息序号跳变。
    """
    return {
        "id": item.id,
        "group_id": item.group,
        "user_id": item.user,
        "username": username,
        "content": "" if item.is_deleted else item.content,
        "message_type": item.message_type,
        "attachment_url": item.attachment_url,
        "parent_message": item.parent_message,
        "is_deleted": bool(item.is_deleted),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _parse_group_id(channel: Any) -> Optional[int]:
    """从 ``chat:group:{id}`` 频道名解析 group_id（兼容 bytes / str 频道）"""
    if not channel:
        return None
    text = channel.decode() if isinstance(channel, (bytes, bytearray)) else str(channel)
    if not text.startswith(CHANNEL_PREFIX):
        return None
    suffix = text[len(CHANNEL_PREFIX):]
    return int(suffix) if suffix.isdigit() else None


class GroupBroadcaster:
    """``chat:group:{group_id}`` 频道的广播器（跨进程 + 降级）。

    本类同时扮演「发布者」和「订阅者」：每个 worker 一份单例，负责把 Redis 消息
    扇出给本进程内订阅了该群的 WebSocket 连接；Redis 不可用时退化为直接进程内扇出。
    """

    def __init__(self) -> None:
        self._subscribers: dict[int, dict[str, WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._redis: Any = None
        self._redis_checked = False
        self._listener: Optional[asyncio.Task] = None

    # ------------------------------------------------------------ Redis
    async def _client(self) -> Any:
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            from src.services.redis_service import redis_service

            self._redis = redis_service.redis
            logger.info("群聊消息已接入 Redis（chat:group:* 跨 worker 广播）")
        except Exception as exc:  # noqa: BLE001 - Redis 不可用是允许的降级路径
            self._redis = None
            logger.warning(
                "Redis 不可用（%s）：群聊消息降级为**进程内广播**，"
                "多 worker 下同一群的消息不会跨进程送达",
                exc,
            )
        return self._redis

    async def start(self) -> None:
        """启动 psubscribe 监听（幂等）"""
        client = await self._client()
        if client is None or self._listener is not None:
            return
        self._listener = asyncio.create_task(self._listen(client))

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            self._listener = None

    async def _listen(self, client: Any) -> None:
        try:
            pubsub = client.pubsub()
            await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
            async for message in pubsub.listen():
                if message.get("type") != "pmessage":
                    continue
                group_id = _parse_group_id(message.get("channel"))
                if group_id is None:
                    continue
                try:
                    payload = json.loads(message["data"])
                except (ValueError, TypeError):
                    continue
                await self._fanout(group_id, payload)
        except asyncio.CancelledError:  # pragma: no cover - 正常关闭路径
            raise
        except Exception:  # noqa: BLE001 - 监听失败不应拖垮进程
            logger.exception("群聊消息 Redis 订阅中断")

    # ------------------------------------------------------------ 订阅表
    async def subscribe(self, group_id: int, client_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers.setdefault(group_id, {})[client_id] = websocket
        await self.start()

    async def unsubscribe(self, group_id: int, client_id: str) -> None:
        async with self._lock:
            conns = self._subscribers.get(group_id)
            if not conns:
                return
            conns.pop(client_id, None)
            if not conns:
                self._subscribers.pop(group_id, None)

    async def _fanout(self, group_id: int, payload: dict) -> None:
        """只发给**本进程**内订阅了该群的连接"""
        conns = self._subscribers.get(group_id)
        if not conns:
            return
        data = json.dumps(payload, ensure_ascii=False, default=str)
        for client_id, websocket in list(conns.items()):
            try:
                await websocket.send_text(data)
            except Exception:  # noqa: BLE001 - 连接已断开，顺手清理
                async with self._lock:
                    current = self._subscribers.get(group_id)
                    if current is not None:
                        current.pop(client_id, None)

    # ------------------------------------------------------------ 广播
    async def broadcast(self, group_id: int, payload: dict) -> None:
        """发布一条群消息：Redis 可用则 ``PUBLISH``，否则进程内扇出（降级）"""
        client = await self._client()
        if client is None:
            await self._fanout(group_id, payload)
            return
        try:
            await client.publish(
                channel_of(group_id),
                json.dumps(payload, ensure_ascii=False, default=str),
            )
        except Exception:  # noqa: BLE001 - 发布失败退回进程内，至少本进程能收到
            logger.exception("群聊消息广播发布失败: group_id=%s", group_id)
            await self._fanout(group_id, payload)


group_broadcaster = GroupBroadcaster()


class ChatMessageService:
    """群聊消息（chat 域）：历史列表 / 发送 / 撤回。"""

    # ------------------------------------------------------------ 成员校验
    async def is_member(self, db: AsyncSession, group_id: int, user_id: int) -> bool:
        """该用户是否为群成员（WS 准入与 HTTP 校验共用；群不存在时为 False）"""
        member_id = (
            await db.execute(
                select(ChatGroupMember.id).where(
                    ChatGroupMember.group == group_id, ChatGroupMember.user == user_id
                )
            )
        ).scalar()
        return member_id is not None

    async def _require_group(self, db: AsyncSession, group_id: int) -> ChatGroup:
        group = await db.get(ChatGroup, group_id)
        if group is None:
            raise NotFoundError("群聊不存在")
        return group

    async def _require_member(
        self, db: AsyncSession, group_id: int, user_id: int
    ) -> ChatGroup:
        group = await self._require_group(db, group_id)
        if not await self.is_member(db, group_id, user_id):
            raise ForbiddenError("你不是该群成员")
        return group

    # ------------------------------------------------------------ 列表
    async def list_messages(
        self,
        db: AsyncSession,
        group_id: int,
        user_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """群内消息（分页）。

        先按时间倒序取最新 N 条（``page=1`` 即最近一段），再**反转成升序**返回 ——
        聊天窗口习惯。撤回消息一并返回（``content`` 置空）。
        """
        await self._require_member(db, group_id, user_id)

        total = int(
            (
                await db.execute(
                    select(func.count()).select_from(ChatMessage).where(
                        ChatMessage.group == group_id
                    )
                )
            ).scalar()
            or 0
        )
        rows = (
            await db.execute(
                select(ChatMessage)
                .where(ChatMessage.group == group_id)
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
            )
        ).scalars().all()

        name_map = await self._usernames(db, [row.user for row in rows])
        items = [serialize_message(row, username=name_map.get(row.user)) for row in rows]
        items.reverse()
        return items, total

    # ------------------------------------------------------------ 发送
    async def create_message(
        self, db: AsyncSession, user_id: int, payload: ChatMessageCreate
    ) -> dict:
        """落库 + 更新群的 ``last_message_at`` + 广播给群频道"""
        group = await self._require_member(db, payload.group_id, user_id)
        now = datetime.now()
        item = ChatMessage(
            group=payload.group_id,
            user=user_id,
            content=payload.content,
            message_type=payload.message_type,
            attachment_url=payload.attachment_url,
            parent_message=payload.parent_message,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        db.add(item)
        group.last_message_at = now
        group.updated_at = now
        await db.commit()
        await db.refresh(item)

        username = (
            await db.execute(select(UserModel.username).where(UserModel.id == user_id))
        ).scalar()
        data = serialize_message(item, username=username)
        await group_broadcaster.broadcast(payload.group_id, data)
        return data

    # ------------------------------------------------------------ 撤回
    async def recall_message(self, db: AsyncSession, user_id: int, message_id: int) -> None:
        """撤回本人消息（软删除 ``is_deleted=True`` 并广播 ``{type: recall, ...}``）。

        非本人 → 403；消息不存在 → 404。重复撤回幂等（不重复落库，但仍广播）。
        """
        item = await db.get(ChatMessage, message_id)
        if item is None:
            raise NotFoundError("消息不存在")
        if item.user != user_id:
            raise ForbiddenError("只能撤回本人发送的消息")

        if not item.is_deleted:
            item.is_deleted = True
            item.updated_at = datetime.now()
            await db.commit()

        await group_broadcaster.broadcast(
            item.group, {"type": "recall", "id": item.id, "group_id": item.group}
        )

    # ------------------------------------------------------------ 工具
    @staticmethod
    async def _usernames(
        db: AsyncSession, user_ids: list[Any]
    ) -> dict[int, Optional[str]]:
        """批量取用户名（一次查询，避免 N+1）"""
        ids = {int(uid) for uid in user_ids if uid is not None}
        if not ids:
            return {}
        rows = (
            await db.execute(
                select(UserModel.id, UserModel.username).where(UserModel.id.in_(ids))
            )
        ).all()
        return {int(uid): username for uid, username in rows}


chat_message_service = ChatMessageService()
