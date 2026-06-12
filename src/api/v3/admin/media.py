"""
V3 媒体管理 API

权限要求:
  GET    /media            → media:view
  POST   /media/upload     → media:upload
  DELETE /media/{id}       → media:delete

路由函数内无权限查询。
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.media import Media
from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db, get_current_user
from src.api.v3._permission import Permission
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-media"])


# ============================================================
# 列表
# ============================================================

@router.get("/media", summary="媒体列表")
async def list_media(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    media_type: Optional[str] = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("media:view")),
):
    query = select(Media)

    if media_type:
        query = query.where(Media.media_type == media_type)

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Media.created_at.desc()).offset(offset).limit(per_page)
    )
    items = result.scalars().all()

    return ApiResponse(success=True, data={
        "media": [_media_to_dict(m) for m in items],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    })


# ============================================================
# 上传
# ============================================================

@router.post("/media/upload", summary="上传文件")
async def upload_media(
    file: UploadFile = File(...),
    folder_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(Permission("media:upload")),
):
    """上传媒体文件"""
    # 读取文件内容
    content = await file.read()

    # 保存文件到存储
    from src.api.v2.media_v1pack.upload_service import save_uploaded_file
    result = save_uploaded_file(
        file_content=content,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        user_id=current_user.id,
    )

    if not result.get("success"):
        return ApiResponse(success=False, error=result.get("error", "上传失败"))

    # 写入数据库
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    media = Media(
        filename=result["filename"],
        original_filename=file.filename,
        filepath=result["filepath"],
        media_type=result.get("media_type", "image"),
        file_size=len(content),
        mime_type=file.content_type,
        user_id=current_user.id,
        folder_id=folder_id,
        created_at=now,
        updated_at=now,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)

    return ApiResponse(success=True, data=_media_to_dict(media), message="上传成功")


# ============================================================
# 删除
# ============================================================

@router.delete("/media/{media_id}", summary="删除文件")
async def delete_media(
    media_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("media:delete")),
):
    media = await db.get(Media, media_id)
    if not media:
        return ApiResponse(success=False, error="文件不存在")

    # 删除物理文件
    import os
    filepath = media.filepath
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except OSError as e:
            logger.warning(f"删除物理文件失败: {filepath} — {e}")

    await db.delete(media)
    await db.commit()

    return ApiResponse(success=True, message="文件已删除")


# ============================================================
# 辅助函数
# ============================================================

def _media_to_dict(m: Media) -> dict:
    return {
        "id": m.id,
        "filename": m.filename,
        "original_filename": getattr(m, 'original_filename', None),
        "media_type": m.media_type,
        "file_size": m.file_size,
        "mime_type": getattr(m, 'mime_type', None),
        "url": m.filepath,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
