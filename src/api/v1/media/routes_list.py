"""
媒体列表、统计、分类、标签查询
"""

from decimal import Decimal
from pathlib import Path
from typing import Optional

import humanize
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.media import Media
from src.api.v1.core.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from .dependencies import get_user_storage_used, get_user_storage_limit
from .utils import convert_storage_size

router = APIRouter()
from src.unified_logger import default_logger as logger


# ---------- 列表 ----------
@router.get("/files")
@router.get("/files/list")
async def list_media(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db),
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        q: Optional[str] = Query(None, description="搜索关键词"),
        media_type: str = Query("all", description="媒体类型: all, image, video, audio, document"),
        category: Optional[str] = Query(None, description="分类筛选"),
        folder_name: Optional[str] = Query(None, description="文件夹名称（使用名称而非ID，避免暴露系统设计）"),
        sort_by: str = Query("created_at_desc", description="排序方式"),
        date_from: Optional[str] = Query(None),
        date_to: Optional[str] = Query(None),
        min_size: Optional[int] = Query(None),
        max_size: Optional[int] = Query(None)
):
    """获取媒体文件列表（优化版：移除 FileHash JOIN 提升性能）"""
    try:
        user_id = current_user_obj.id
        offset = (page - 1) * per_page

        base_query = select(Media).where(Media.user == user_id)

        # 如果指定了文件夹名称（支持路径，如 folder1/folder2）
        if folder_name:
            from shared.models.media.media_folder import MediaFolder as MF

            from urllib.parse import unquote
            folder_path = unquote(folder_name)
            path_parts = [p.strip() for p in folder_path.split('/') if p.strip()]

            if path_parts:
                current_parent_id = None
                target_folder_id = None

                for i, part_name in enumerate(path_parts):
                    folder_query = select(MF.id).where(
                        MF.name == part_name,
                        MF.user == user_id,
                        MF.parent_id == current_parent_id
                    )
                    folder_result = await db.execute(folder_query)
                    folder_id = folder_result.scalar_one_or_none()
                    if not folder_id:
                        return {
                            "success": True,
                            "data": {
                                "media_items": [],
                                "pagination": {
                                    "current_page": page, "pages": 0, "total": 0,
                                    "has_prev": False, "has_next": False, "per_page": per_page
                                },
                                "stats": {
                                    'image_count': 0, 'video_count': 0, 'audio_count': 0,
                                    'document_count': 0, 'storage_used': '0 B',
                                    'storage_total': '0 B', 'storage_percentage': 0,
                                    'canBeUploaded': True, 'totalUsed': 0
                                }
                            }
                        }
                    if i == len(path_parts) - 1:
                        target_folder_id = folder_id
                    else:
                        current_parent_id = folder_id

                if target_folder_id:
                    base_query = base_query.where(Media.folder_id == target_folder_id)
        else:
            base_query = base_query.where(Media.folder_id.is_(None))

        if q:
            base_query = base_query.where(Media.original_filename.ilike(f"%{q}%"))
        if category and category != 'all' and hasattr(Media, 'category'):
            base_query = base_query.where(Media.category == category)

        mime_filters = {
            'image': Media.mime_type.startswith('image'),
            'video': Media.mime_type.startswith('video'),
            'audio': Media.mime_type.startswith('audio'),
            'document': Media.mime_type.in_([
                'application/pdf', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/plain', 'text/markdown'
            ]),
            'application/pdf': Media.mime_type == 'application/pdf',
            'application/zip': Media.mime_type.in_([
                'application/zip', 'application/x-rar-compressed',
                'application/x-7z-compressed', 'application/gzip',
                'application/x-tar', 'application/x-bzip2'
            ])
        }
        if media_type != 'all' and media_type in mime_filters:
            base_query = base_query.where(mime_filters[media_type])

        if date_from:
            base_query = base_query.where(Media.created_at >= date_from)
        if date_to:
            base_query = base_query.where(Media.created_at <= date_to)
        if min_size is not None:
            base_query = base_query.where(Media.file_size >= min_size)
        if max_size is not None:
            base_query = base_query.where(Media.file_size <= max_size)

        sort_mapping = {
            'created_at_desc': Media.created_at.desc(),
            'created_at_asc': Media.created_at.asc(),
            'filename_asc': Media.original_filename.asc(),
            'filename_desc': Media.original_filename.desc(),
        }
        order_by = sort_mapping.get(sort_by, Media.created_at.desc())

        paginated_query = base_query.order_by(order_by).offset(offset).limit(per_page)
        media_result = await db.execute(paginated_query)
        media_list = media_result.scalars().all()

        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        storage_used = await get_user_storage_used(user_id, db)
        storage_total_bytes = await get_user_storage_limit(user_id, db)
        storage_total_bytes = Decimal(str(storage_total_bytes))

        # N+1 修复: 使用独立的轻量查询获取统计
        user_media_subq = select(Media.id, Media.mime_type, Media.file_size).where(Media.user == user_id).subquery()
        stats_query = select(
            func.count().label('total_count'),
            func.sum(case((user_media_subq.c.mime_type.startswith('image'), 1), else_=0)).label('image_count'),
            func.sum(case((user_media_subq.c.mime_type.startswith('video'), 1), else_=0)).label('video_count'),
            func.sum(case((user_media_subq.c.mime_type.startswith('audio'), 1), else_=0)).label('audio_count'),
            func.sum(case((user_media_subq.c.mime_type.in_([
                'application/pdf', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/plain', 'text/markdown'
            ]), 1), else_=0)).label('document_count')
        ).select_from(user_media_subq)
        stats_result = await db.execute(stats_query)
        stats_row = stats_result.first()

        storage_percentage = min(100, int((storage_used / storage_total_bytes * 100))) if storage_total_bytes > 0 else 0

        media_items = []
        for media in media_list:
            media_items.append({
                'id': media.id,
                'filename': media.filename,
                'original_filename': media.original_filename,
                'title': media.original_filename,
                'hash': media.hash,
                'file_path': media.file_path,
                'file_url': media.file_url,
                'url': media.file_url,
                'thumbnail_url': media.thumbnail_url,
                'mime_type': media.mime_type,
                'media_type': media.file_type,
                'file_size': media.file_size,
                'width': media.width,
                'height': media.height,
                'description': media.description,
                'alt_text': media.alt_text,
                'category': media.category,
                'tags': media.tags,
                'created_at': media.created_at.isoformat() if media.created_at else None,
                'updated_at': media.updated_at.isoformat() if media.updated_at else None
            })

        total_pages = max(1, (total + per_page - 1) // per_page)

        return {
            "success": True,
            "data": {
                "media_items": media_items,
                "pagination": {
                    "current_page": page, "pages": total_pages, "total": total,
                    "has_prev": page > 1, "has_next": page < total_pages, "per_page": per_page
                },
                "stats": {
                    'image_count': int(stats_row.image_count or 0),
                    'video_count': int(stats_row.video_count or 0),
                    'audio_count': int(stats_row.audio_count or 0),
                    'document_count': int(stats_row.document_count or 0),
                    'storage_used': humanize.naturalsize(storage_used),
                    'storage_total': convert_storage_size(storage_total_bytes),
                    'storage_percentage': storage_percentage,
                    'canBeUploaded': (storage_total_bytes - storage_used) > 1024,
                    'totalUsed': storage_used
                }
            }
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"获取媒体列表失败: {str(e)}\n{error_trace}")
        return JSONResponse(
            {'success': False, 'message': '获取媒体文件列表失败', 'error': str(e), 'traceback': error_trace},
            status_code=500
        )


# ---------- 统计 ----------
@router.get("/statistics")
async def get_media_statistics(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    from shared.services.media.media_manager import media_library_service
    try:
        result = await media_library_service.get_media_statistics(db)
        if result["success"]:
            return ApiResponse(success=True, data=result["statistics"])
        return ApiResponse(success=False, error=result["error"])
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ---------- 分类（增强：包含文件数量）----------
@router.get("/categories")
async def get_categories(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """获取所有媒体分类及每个分类下的文件数量"""
    try:
        query = (
            select(Media.category, func.count(Media.id).label('count'))
            .where(Media.category != None)
            .group_by(Media.category)
        )
        result = await db.execute(query)
        categories_with_count = result.all()
        categories = [
            {"name": row[0], "count": row[1]}
            for row in categories_with_count if row[0]
        ]
        categories.sort(key=lambda x: x['name'])
        return ApiResponse(success=True, data={"categories": categories})
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ---------- 标签汇总（增强：包含使用次数）----------
@router.get("/tags")
async def get_all_tags(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """获取所有媒体标签及使用次数"""
    try:
        query = select(Media.tags).where(Media.tags != None)
        result = await db.execute(query)
        all_tags_str = [row[0] for row in result.all() if row[0]]

        tag_count = {}
        for tags_str in all_tags_str:
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            for tag in tags:
                tag_count[tag] = tag_count.get(tag, 0) + 1

        tags = [
            {"name": name, "count": count}
            for name, count in tag_count.items()
        ]
        tags.sort(key=lambda x: x['count'], reverse=True)
        return ApiResponse(success=True, data={"tags": tags})
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ---------- 视频缩略图 ----------
@router.get("/thumbnail/{media_id}")
async def get_video_thumbnail(
        media_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    获取视频缩略图

    Args:
        media_id: 媒体文件ID

    Returns:
        缩略图文件或404
    """
    try:
        # 查询媒体记录
        query = select(Media).where(Media.id == media_id)
        result = await db.execute(query)
        media = result.scalar_one_or_none()

        if not media:
            return JSONResponse(
                content={"success": False, "error": "媒体文件不存在"},
                status_code=404
            )

        # 检查是否有缩略图
        if not media.thumbnail_path:
            return JSONResponse(
                content={"success": False, "error": "缩略图不存在"},
                status_code=404
            )

        # 从存储中读取缩略图
        from src.utils.storage.s3_storage import s3_storage
        thumbnail_data = s3_storage.read_file(media.thumbnail_path)

        if not thumbnail_data:
            return JSONResponse(
                content={"success": False, "error": "无法读取缩略图"},
                status_code=404
            )

        # 返回缩略图
        return Response(
            content=thumbnail_data,
            media_type='image/jpeg',
            headers={
                'Cache-Control': 'public, max-age=86400',  # 缓存1天
                'Content-Disposition': f'inline; filename="{Path(media.thumbnail_path).name}"'
            }
        )

    except Exception as e:
        logger.error(f"获取视频缩略图失败: {str(e)}", exc_info=True)
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )
