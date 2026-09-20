"""mobile/message 的业务逻辑（前台站内信，表 ``private_messages``）

约束：

1. **归属**：已读标记仅收件人可做；删除仅收发双方可做；归属不符一律 404
   （不泄露记录存在性，与 ``mobile/article`` 的 ``_mine_or_404`` 同一约定）。
2. **双向软删**：``is_deleted_by_sender`` / ``is_deleted_by_recipient`` 各自独立——
   一方删除后自己侧不可见，对方仍可见；两侧都删才算双方不可见。
3. **可见性**：列表/会话查询一律排除"我已删除"（按我在消息中的角色选对应标志，
   列允许 NULL，用 ``isnot(True)`` 而非 ``is_(False)``）。
4. 发送：不能给自己发（400）；收件人不存在 404；回复的父消息不存在 404。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import PrivateMessage
from shared.models.user import User as UserModel
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.modules.mobile.message.schema import MobileMessageCreate


def _message_out(item: PrivateMessage, *, user_id: int) -> dict:
    """按当前用户视角序列化一条消息（direction 相对当前用户而言）"""
    return {
        "id": item.id,
        "direction": "out" if item.sender == user_id else "in",
        "content": item.content,
        "message_type": item.message_type,
        "attachment_url": item.attachment_url,
        "is_read": bool(item.is_read),
        "created_at": item.created_at,
    }


class MobileMessageService:
    """前台站内信（全部以当前用户为界）"""

    # ------------------------------------------------------------ 会话列表
    async def list_contacts(self, db: AsyncSession, *, user_id: int) -> list[dict]:
        """与我相关的会话列表（排除我已删除的消息），最近活跃在前。

        每个会话取最新一条可见消息（id 单调递增，用 ``max(id)`` 定位）；
        ``unread`` 统计对方发给我、我未读且我未删的消息数；
        ``peer_name`` 取 ``users.username``（users 表没有昵称列，username 可为 NULL）。
        """
        peer = case(
            (PrivateMessage.sender == user_id, PrivateMessage.recipient),
            else_=PrivateMessage.sender,
        ).label("peer")
        visible = _visible_for(user_id)

        # 每个会话最新一条可见消息
        last_sq = (
            select(peer, func.max(PrivateMessage.id).label("last_id"))
            .where(visible)
            .group_by(peer)
            .subquery()
        )
        last_rows = (
            await db.execute(
                select(PrivateMessage, last_sq.c.peer).join(
                    last_sq, PrivateMessage.id == last_sq.c.last_id
                )
            )
        ).all()

        # 未读数：对方发给我、我未读、我未删
        unread_rows = (
            await db.execute(
                select(peer, func.count())
                .where(
                    PrivateMessage.recipient == user_id,
                    PrivateMessage.is_read.isnot(True),
                    PrivateMessage.is_deleted_by_recipient.isnot(True),
                )
                .group_by(peer)
            )
        ).all()
        unread_map = {int(row_peer): int(count) for row_peer, count in unread_rows}

        # 对方用户名（一次批量查，避免 N+1）
        name_map: dict[int, Optional[str]] = {}
        peer_ids = [int(row_peer) for _, row_peer in last_rows]
        if peer_ids:
            name_rows = (
                await db.execute(
                    select(UserModel.id, UserModel.username).where(UserModel.id.in_(peer_ids))
                )
            ).all()
            name_map = {int(uid): username for uid, username in name_rows}

        contacts = [
            {
                "peer_id": int(row_peer),
                "peer_name": name_map.get(int(row_peer)),
                "last_content": message.content,
                "last_at": message.created_at,
                "unread": unread_map.get(int(row_peer), 0),
            }
            for message, row_peer in last_rows
        ]
        # 最近活跃在前；created_at 为 NULL 的老数据沉底
        contacts.sort(key=lambda c: (c["last_at"] is not None, c["last_at"]), reverse=True)
        return contacts

    # ------------------------------------------------------------ 会话详情
    async def list_conversation(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        peer_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """与某用户的双向私信（时间正序），排除我侧已删除的消息"""
        where = and_(
            or_(
                and_(
                    PrivateMessage.sender == user_id,
                    PrivateMessage.recipient == peer_id,
                ),
                and_(
                    PrivateMessage.sender == peer_id,
                    PrivateMessage.recipient == user_id,
                ),
            ),
            _visible_for(user_id),
        )

        total = int(
            (
                await db.execute(select(func.count()).select_from(PrivateMessage).where(where))
            ).scalar()
            or 0
        )
        items = (
            (
                await db.execute(
                    select(PrivateMessage)
                    .where(where)
                    .order_by(PrivateMessage.created_at.asc(), PrivateMessage.id.asc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return [_message_out(item, user_id=user_id) for item in items], total

    # ------------------------------------------------------------ 发送
    async def send(
        self, db: AsyncSession, *, user_id: int, payload: MobileMessageCreate
    ) -> dict:
        """发送私信；收件人/父消息不存在 404，发给自己 400"""
        if payload.recipient_id == user_id:
            raise BadRequestError("不能给自己发送消息")

        recipient_exists = (
            await db.execute(
                select(UserModel.id).where(UserModel.id == payload.recipient_id)
            )
        ).scalar()
        if recipient_exists is None:
            raise NotFoundError("收件人不存在")

        if payload.parent_message is not None:
            parent_exists = (
                await db.execute(
                    select(PrivateMessage.id).where(PrivateMessage.id == payload.parent_message)
                )
            ).scalar()
            if parent_exists is None:
                raise NotFoundError("回复的父消息不存在")

        now = datetime.now()
        item = PrivateMessage(
            sender=user_id,
            recipient=payload.recipient_id,
            content=payload.content,
            message_type=payload.message_type,
            attachment_url=payload.attachment_url,
            parent_message=payload.parent_message,
            is_read=False,
            is_deleted_by_sender=False,
            is_deleted_by_recipient=False,
            created_at=now,
            updated_at=now,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return _message_out(item, user_id=user_id)

    # ------------------------------------------------------------ 已读
    async def mark_read(self, db: AsyncSession, *, user_id: int, message_id: int) -> dict:
        """标记已读；仅收件人可操作，非本人收件 404（不泄露存在性）"""
        item = (
            await db.execute(
                select(PrivateMessage).where(
                    PrivateMessage.id == message_id,
                    PrivateMessage.recipient == user_id,
                )
            )
        ).scalars().first()
        if item is None:
            raise NotFoundError("消息不存在")

        if not item.is_read:
            item.is_read = True
            item.read_at = datetime.now()
            item.updated_at = datetime.now()
            await db.commit()
            await db.refresh(item)
        return {"id": item.id, "is_read": bool(item.is_read), "read_at": item.read_at}

    # ------------------------------------------------------------ 删除
    async def delete(self, db: AsyncSession, *, user_id: int, message_id: int) -> None:
        """删除消息（双向软删：只置当前用户一侧的标志）；非收发双方 404"""
        item = (
            await db.execute(select(PrivateMessage).where(PrivateMessage.id == message_id))
        ).scalars().first()
        if item is None or user_id not in (item.sender, item.recipient):
            raise NotFoundError("消息不存在")

        if item.sender == user_id:
            item.is_deleted_by_sender = True
        if item.recipient == user_id:
            item.is_deleted_by_recipient = True
        item.updated_at = datetime.now()
        await db.commit()


def _visible_for(user_id: int):
    """我对某条消息可见 = 我在消息中且对应一侧未删除（标志允许 NULL）"""
    return or_(
        and_(
            PrivateMessage.sender == user_id,
            PrivateMessage.is_deleted_by_sender.isnot(True),
        ),
        and_(
            PrivateMessage.recipient == user_id,
            PrivateMessage.is_deleted_by_recipient.isnot(True),
        ),
    )


mobile_message_service = MobileMessageService()
