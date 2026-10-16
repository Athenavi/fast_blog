"""yjs 实时协同：**真实 CRDT 房间** + Redis 跨进程广播（T5-11 批次 9）

**与 v2 的差异**（v2 的 "yjs" 不是真 yjs，逐条对照）：

| v2 的做法 | 问题 | 本模块 |
|---|---|---|
| `update_state` 只做 `self.state = update`（存"最后一帧"） | 没有 CRDT 合并，也没有 sync step1/step2 → 标准 yjs 客户端**无法完成初始同步** | 用 ``pycrdt.Doc`` **真实合并**（``apply_update`` / ``get_update`` / ``handle_sync_message``），完整实现 y-protocols 的 sync 三步 |
| 广播 = 遍历**进程内** ``doc.clients`` | 多 worker 下同一文档连到不同进程互不可见，各自维护副本并各自覆盖 DB | 状态与广播都走 **Redis**（``GET/SET`` 存合并后状态 + ``PUBLISH/PSUBSCRIBE`` 扇出）；Redis 不在时降级为进程内广播并**明确告警** |
| WS 鉴权失败也放行（``payload=None`` → 匿名） | 知道 document_id 就能读写任意文档 | 鉴权失败**关闭连接**；文档归属由 ``invite_service.require_document_access``（作者本人或持有效邀请码）把关 |
| 无持久化 CRDT 状态 | 重启即丢 | 合并后的状态写 Redis；前端上报的 HTML 快照落 ``article_content`` |

**关于 WS 鉴权通道**：浏览器 WebSocket API **无法自定义请求头**，所以这里按
「Cookie ``access_token`` → 子协议 ``Sec-WebSocket-Protocol`` → query ``token``」三级回退。
query 会进访问日志，属于最次选，仅在前两种拿不到时使用。
"""

import asyncio
import base64
import json
import uuid
from typing import Any, Optional

from fastapi import WebSocket
from pycrdt import (
    Awareness,
    Doc,
    create_sync_message,
    create_update_message,
)

from src.api.v3.core.logger import get_logger

logger = get_logger("content.collaboration.yjs")

#: Redis 频道前缀（每个文档一条频道）
CHANNEL_PREFIX = "fastblog:yjs:"
#: Redis 里存"合并后 CRDT 状态"的键前缀
STATE_PREFIX = "fastblog:yjs-state:"
#: 房间空置多久后回收（秒）
ROOM_TTL_SECONDS = 30 * 60


def _channel(document_id: int) -> str:
    return f"{CHANNEL_PREFIX}{document_id}"


def _state_key(document_id: int) -> str:
    return f"{STATE_PREFIX}{document_id}"


class Room:
    """一个文档的 CRDT 房间"""

    def __init__(self, document_id: int) -> None:
        self.document_id = document_id
        self.doc = Doc()
        self.awareness = Awareness(self.doc)
        self.clients: dict[str, WebSocket] = {}
        #: 最后一份由客户端上报的 HTML 快照（落库用；CRDT 二进制状态本身不落库，见模块 docstring）
        self.html_snapshot: Optional[str] = None

    def add(self, client_id: str, websocket: WebSocket) -> None:
        self.clients[client_id] = websocket

    def remove(self, client_id: str) -> None:
        self.clients.pop(client_id, None)

    @property
    def empty(self) -> bool:
        return not self.clients

    @property
    def client_count(self) -> int:
        return len(self.clients)

    def full_state(self) -> bytes:
        """当前完整状态（y-protocols update 编码）"""
        return self.doc.get_update()

    def step1(self) -> bytes:
        """给新连接的 sync step1（状态向量）"""
        return create_sync_message(self.doc)

    def apply_update(self, update: bytes) -> None:
        self.doc.apply_update(update)

    def update_message(self, update: bytes) -> bytes:
        """把一段增量包成 y-protocols 的 update 帧"""
        return create_update_message(update)


class RoomRegistry:
    """房间注册表 + 跨进程广播

    广播路径：``broadcast()`` → 本地扇出 + ``PUBLISH``；每个 worker 的 listener 收到
    其它 worker 的消息后再扇出给**自己进程内**的连接（发布者会忽略自己发的，避免重复）。
    """

    def __init__(self) -> None:
        self._rooms: dict[int, Room] = {}
        self._lock = asyncio.Lock()
        self._redis: Any = None
        self._redis_checked = False
        self._listener: Optional[asyncio.Task] = None
        #: 本进程实例标识（用于忽略自己发布的 Redis 消息，避免重复扇出）
        self._instance_id = uuid.uuid4().hex[:12]

    # ------------------------------------------------------------ Redis
    async def _client(self) -> Any:
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            from src.services.redis_service import redis_service

            self._redis = redis_service.redis
            logger.info("yjs 房间已接入 Redis（跨 worker 共享状态与广播）")
        except Exception as exc:  # noqa: BLE001 - Redis 不可用是允许的降级路径
            self._redis = None
            logger.warning(
                "Redis 不可用（%s）：yjs 房间降级为**进程内广播**，多 worker 下不共享状态", exc
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
                try:
                    envelope = json.loads(message["data"])
                except (ValueError, TypeError):
                    continue
                if envelope.get("origin") == self._instance_id:
                    continue  # 自己发的，本地已经扇出过
                document_id = envelope.get("document_id")
                payload = envelope.get("payload")
                if not isinstance(document_id, int) or not payload:
                    continue
                try:
                    frame = base64.b64decode(payload)
                except (ValueError, TypeError):
                    continue
                room = self._rooms.get(document_id)
                if room is not None:
                    await self._fanout(room, frame, exclude=None)
        except asyncio.CancelledError:  # pragma: no cover - 正常关闭路径
            raise
        except Exception:  # noqa: BLE001 - 监听失败不应拖垮进程
            logger.exception("yjs Redis 订阅中断")

    # ------------------------------------------------------------ 房间
    async def room(self, document_id: int) -> Room:
        async with self._lock:
            room = self._rooms.get(document_id)
            if room is None:
                room = Room(document_id)
                self._rooms[document_id] = room
                await self._restore(room)
            return room

    async def release(self, room: Room) -> None:
        """房间空了：把合并后的状态回写 Redis 并移除（下次连接会从 Redis 恢复）"""
        async with self._lock:
            if not room.empty:
                return
            await self._persist(room)
            self._rooms.pop(room.document_id, None)

    async def _restore(self, room: Room) -> None:
        client = await self._client()
        if client is None:
            return
        try:
            raw = await client.get(_state_key(room.document_id))
        except Exception:  # noqa: BLE001
            logger.exception("读取 yjs 状态失败: document_id=%s", room.document_id)
            return
        if raw:
            # decode_responses=True 时二进制会被 latin-1 解码，这里原样编回
            update = raw if isinstance(raw, bytes) else str(raw).encode("latin-1")
            room.apply_update(update)

    async def _persist(self, room: Room) -> None:
        client = await self._client()
        if client is None:
            return
        try:
            # 带 TTL：房间状态不会在 Redis 里无限累积
            await client.set(_state_key(room.document_id), room.full_state(), ex=ROOM_TTL_SECONDS)
        except Exception:  # noqa: BLE001
            logger.exception("写入 yjs 状态失败: document_id=%s", room.document_id)

    # ------------------------------------------------------------ 广播
    async def _fanout(self, room: Room, frame: bytes, exclude: Optional[str]) -> None:
        """只发给**本进程**内该房间的连接"""
        for client_id, websocket in list(room.clients.items()):
            if client_id == exclude:
                continue
            try:
                await websocket.send_bytes(frame)
            except Exception:  # noqa: BLE001 - 连接已断开
                room.remove(client_id)

    async def broadcast(self, room: Room, frame: bytes, exclude: Optional[str] = None) -> None:
        """本地扇出 + 可选发布到 Redis（其它 worker 的监听器会再扇出）"""
        await self._fanout(room, frame, exclude)
        client = await self._client()
        if client is None:
            return
        try:
            await client.publish(
                _channel(room.document_id),
                json.dumps(
                    {
                        "origin": self._instance_id,
                        "document_id": room.document_id,
                        "payload": base64.b64encode(frame).decode(),
                    }
                ),
            )
        except Exception:  # noqa: BLE001
            logger.exception("yjs 广播发布失败: document_id=%s", room.document_id)

    async def persist_state(self, room: Room) -> None:
        await self._persist(room)

    def snapshot(self) -> list[dict]:
        """**本进程**房间快照（只读；跨 worker 的房间状态在 Redis 里，不在此列）"""
        return [
            {"document_id": room.document_id, "clients": room.client_count}
            for room in self._rooms.values()
        ]


room_registry = RoomRegistry()
