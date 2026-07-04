"""
MCP 媒体管理工具处理器
权限：删除媒体需要本人或管理员
"""
from sqlalchemy import select

from shared.models.media import Media
from src.mcp._context import get_user_ctx
from src.utils.database.main import get_async_session_context


def _require_auth():
    ctx = get_user_ctx()
    if not ctx:
        raise PermissionError("需要登录才能执行此操作")
    return ctx


async def list_media(arguments: dict) -> dict:
    """获取媒体文件列表（所有用户可读）"""
    _require_auth()
    limit = min(arguments.get("limit", 20), 50)
    media_type = arguments.get("media_type", "").strip().lower()

    async with get_async_session_context() as db:
        q = select(Media).order_by(Media.created_at.desc()).limit(limit)
        if media_type:
            prefix = {"image": "image", "video": "video", "audio": "audio", "document": "application"}.get(media_type, media_type)
            q = q.where(Media.mime_type.startswith(prefix))

        media_list = (await db.execute(q)).scalars().all()
        return {"success": True, "total": len(media_list), "media": [{
            "id": m.id, "filename": m.original_filename or m.filename or "unknown",
            "mime_type": m.mime_type or "", "file_size": m.file_size or 0,
            "url": m.file_url or f"/media/{m.filename or ''}" if m.filename else "",
            "alt_text": m.alt_text or "", "category": m.category or "",
            "created_at": m.created_at.isoformat() if m.created_at else "",
        } for m in media_list]}


async def delete_media(arguments: dict) -> dict:
    """删除媒体文件（仅本人或管理员）"""
    ctx = _require_auth()
    media_id = arguments.get("media_id")
    if not media_id:
        raise ValueError("媒体ID不能为空")

    async with get_async_session_context() as db:
        media = await db.scalar(select(Media).where(Media.id == int(media_id)))
        if not media:
            raise ValueError(f"媒体 #{media_id} 不存在")
        if media.user_id != ctx.id and not ctx.is_superuser:
            raise PermissionError("只能删除自己的媒体文件")
        await db.delete(media)
        await db.commit()
        return {"success": True, "message": f"媒体 #{media_id} 已删除", "media_id": media_id}
