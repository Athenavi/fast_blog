"""notification 模块业务逻辑

所有查询/变更都带 ``recipient == user_id`` 条件，避免越权访问他人通知。
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Notification
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.ops.notification.crud import notification_crud

logger = get_logger("notification")


def _out(item: Notification) -> dict:
    return {
        "id": item.id,
        "recipient": item.recipient,
        "type": item.type,
        "title": item.title,
        "message": item.message,
        "is_read": bool(item.is_read),
        "read_at": item.read_at,
        "created_at": item.created_at,
    }


class NotificationService:
    """站内通知（按当前用户过滤）"""

    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        order: str = "desc",
    ) -> Tuple[List[dict], int]:
        filters = {"recipient": user_id}
        if unread_only:
            filters["is_read"] = False

        items, total = await notification_crud.list(
            db,
            page=page,
            page_size=page_size,
            filters=filters,
            order_by="id",
            order=order,
        )
        return [_out(item) for item in items], total

    async def unread_count(self, db: AsyncSession, *, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.recipient == user_id, Notification.is_read.is_(False))
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def mark_read(
        self, db: AsyncSession, *, user_id: int, notification_id: int
    ) -> bool:
        """标记单条已读；不属于该用户时返回 False（不泄露存在性）"""
        stmt = (
            select(Notification)
            .where(Notification.id == notification_id, Notification.recipient == user_id)
        )
        item = (await db.execute(stmt)).scalars().first()
        if item is None:
            return False
        if not item.is_read:
            item.is_read = True
            item.read_at = datetime.now()
            await db.commit()
        return True

    async def mark_all_read(self, db: AsyncSession, *, user_id: int) -> int:
        stmt = (
            sa_update(Notification)
            .where(Notification.recipient == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=datetime.now())
        )
        result = await db.execute(stmt)
        await db.commit()
        return int(result.rowcount or 0)

    async def delete(self, db: AsyncSession, *, user_id: int, notification_id: int) -> bool:
        stmt = (
            sa_delete(Notification)
            .where(Notification.id == notification_id, Notification.recipient == user_id)
        )
        result = await db.execute(stmt)
        await db.commit()
        return bool(result.rowcount)

    async def clean_read(self, db: AsyncSession, *, user_id: int) -> int:
        """清理该用户所有已读通知"""
        stmt = sa_delete(Notification).where(
            Notification.recipient == user_id, Notification.is_read.is_(True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return int(result.rowcount or 0)

    async def create(
        self,
        db: AsyncSession,
        *,
        recipient: int,
        title: str,
        message: Optional[str] = None,
        type: Optional[str] = None,
    ) -> dict:
        """供其他模块内部投递通知使用（非 HTTP 端点）"""
        now = datetime.now()
        item = await notification_crud.create(
            db,
            {
                "recipient": recipient,
                "type": type or "system",
                "title": title,
                "message": message,
                "is_read": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        return _out(item)


notification_service = NotificationService()
