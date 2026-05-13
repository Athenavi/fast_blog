"""
媒体缩略图路由 - 提供基于 media_id 的缩略图访问
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.media import Media
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from src.utils.image.processing import generate_thumbnail as sync_generate_thumbnail

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{media_id}/thumbnail")
async def get_media_thumbnail(
        media_id: int,
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    获取媒体文件的缩略图
    
    Args:
        media_id: 媒体文件ID
        
    Returns:
        缩略图文件或404
    """
    try:
        logger.info(f"收到缩略图请求 - media_id: {media_id}")

        # 查询媒体记录
        query = select(Media).where(Media.id == media_id)
        result = await db.execute(query)
        media = result.scalar_one_or_none()

        if not media:
            logger.warning(f"媒体文件不存在 - media_id: {media_id}")
            raise HTTPException(status_code=404, detail="媒体文件不存在")

        # 检查用户权限（只能访问自己的文件或公开文件）
        if media.user != current_user.id and not media.is_public:
            logger.warning(f"无权访问该媒体文件 - media_id: {media_id}, user: {current_user.id}")
            raise HTTPException(status_code=403, detail="无权访问该媒体文件")

        # 如果已有缩略图路径，直接返回
        if media.thumbnail_path:
            from src.utils.storage.s3_storage import s3_storage
            thumbnail_data = s3_storage.read_file(media.thumbnail_path)

            if thumbnail_data:
                logger.info(f"返回已存在的缩略图 - media_id: {media_id}")
                return Response(
                    content=thumbnail_data,
                    media_type='image/jpeg',
                    headers={
                        'Cache-Control': 'public, max-age=2592000',  # 缓存30天
                        'Content-Disposition': f'inline; filename="thumbnail_{media_id}.jpg"'
                    }
                )

        # 如果没有缩略图，尝试生成
        logger.info(f"缩略图不存在，开始生成 - media_id: {media_id}")

        # 查找原始文件
        original_dir = Path(f"storage/objects/{media.hash[:2]}")
        original_path = None

        # 尝试查找带扩展名或不带扩展名的文件
        path_without_ext = original_dir / media.hash
        if path_without_ext.exists():
            original_path = path_without_ext
        else:
            # 尝试查找带扩展名的文件
            if original_dir.exists():
                for file in original_dir.iterdir():
                    if file.name.startswith(media.hash + '.'):
                        original_path = file
                        break

        if not original_path or not original_path.exists():
            logger.error(f"原始文件不存在 - media_id: {media_id}, hash: {media.hash}")
            raise HTTPException(status_code=404, detail="原始文件不存在")

        # 生成缩略图
        thumb_dir = Path(f"storage/thumbnails/{media.hash[:2]}")
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"{media.hash}.jpg"

        logger.info(f"开始生成缩略图 - media_id: {media_id}, path: {thumb_path}")

        try:
            # 同步生成缩略图（因为 generate_thumbnail 是同步函数）
            success = sync_generate_thumbnail(str(original_path), str(thumb_path), size=(200, 200))

            if success and thumb_path.exists():
                logger.info(f"缩略图生成成功 - media_id: {media_id}")

                # 更新数据库中的缩略图路径
                media.thumbnail_path = f"thumbnails/{media.hash[:2]}/{media.hash}.jpg"
                media.thumbnail_url = f"/api/v2/media/{media_id}/thumbnail"
                await db.commit()

                # 读取并返回缩略图
                with open(thumb_path, 'rb') as f:
                    thumbnail_data = f.read()

                return Response(
                    content=thumbnail_data,
                    media_type='image/jpeg',
                    headers={
                        'Cache-Control': 'public, max-age=2592000',
                        'Content-Disposition': f'inline; filename="thumbnail_{media_id}.jpg"'
                    }
                )
            else:
                logger.warning(f"缩略图生成失败 - media_id: {media_id}")
                raise HTTPException(status_code=404, detail="该文件类型不支持缩略图")
        except Exception as e:
            logger.error(f"生成缩略图时出错 - media_id: {media_id}, error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"生成缩略图失败: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缩略图时发生未预期错误 - media_id: {media_id}, error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取缩略图失败: {str(e)}")
