"""通知模块"""
import json
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import select, update

from shared.models import Notification
from src.extensions import get_async_db_session as get_async_db
async def get_user_notifications(user_id: int, unread_only: bool = False, limit: int = 20):
    """
    获取用户通知
    
    Args:
        user_id: 用户ID
        unread_only: 是否只获取未读通知
        limit: 限制数量
    
    Returns:
        list: 通知列表
    """
    async for session in get_async_db():
        stmt = select(Notification).filter_by(recipient=user_id).order_by(
            Notification.created_at.desc()
        )

        if unread_only:
            stmt = stmt.filter_by(is_read=False)

        if limit:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        return result.scalars().all()


async def mark_notification_as_read(notification_id: int, user_id: int) -> bool:
    """
    标记通知为已读
    
    Args:
        notification_id: 通知ID
        user_id: 用户ID
    
    Returns:
        bool: 是否成功
    """
    async for session in get_async_db():
        stmt = select(Notification).filter_by(
            id=notification_id,
            recipient=user_id
        )
        result = await session.execute(stmt)
        notification = result.scalar_one_or_none()

        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now()
            await session.commit()
            return True

    return False


async def mark_all_notifications_as_read(user_id: int) -> int:
    """
    标记所有通知为已读
    
    Args:
        user_id: 用户ID
    
    Returns:
        int: 更新的通知数量
    """
    async for session in get_async_db():
        stmt = update(Notification).where(
            Notification.recipient == user_id,
            Notification.is_read == False
        ).values(
            is_read=True,
            read_at=datetime.now()
        )

        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount


async def delete_notification(notification_id: int, user_id: int) -> bool:
    """
    删除通知
    
    Args:
        notification_id: 通知ID
        user_id: 用户ID
    
    Returns:
        bool: 是否成功
    """
    async for session in get_async_db():
        stmt = select(Notification).filter_by(
            id=notification_id,
            recipient=user_id
        )
        result = await session.execute(stmt)
        notification = result.scalar_one_or_none()

        if notification:
            await session.delete(notification)
            await session.commit()
            return True

    return False

