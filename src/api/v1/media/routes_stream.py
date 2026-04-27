"""
文件获取、流式传输、范围请求
"""
import urllib.parse
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.file_hash import FileHash
from shared.models.media import Media
from shared.utils.logger import get_logger
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from .utils import PREVIEWABLE_TYPES, handle_local_file, handle_s3_streaming

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{media_id}")
async def get_media_file_by_id(
        media_id: int,
        request: Request,
        range_header: Optional[str] = None,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    try:
        # 查询媒体文件
        media_query = select(Media).where(Media.id == media_id, Media.user == current_user_obj.id)
        media_result = await db.execute(media_query)
        media = media_result.scalar_one_or_none()
        if not media:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 查询文件哈希信息
        file_hash_query = select(FileHash).where(FileHash.hash == media.hash)
        file_hash_result = await db.execute(file_hash_query)
        file_hash = file_hash_result.scalar_one_or_none()
        if not file_hash:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 确定文件路径（用于生成 ETag）
        file_path = Path(f"storage/objects/{media.hash[:2]}/{media.hash}")
        
        # 生成 ETag：直接使用文件修改时间
        try:
            file_stat = file_path.stat() if file_path.exists() else None
            if not file_stat and file_hash.storage_path.startswith("local://"):
                local_path = Path(file_hash.storage_path.replace("local://", "", 1))
                if local_path.exists():
                    file_stat = local_path.stat()
            
            if file_stat:
                etag = f'"{int(file_stat.st_mtime)}"'
            else:
                # 如果文件不存在，使用 hash 作为 ETag
                etag = f'"{media.hash}"'
        except Exception as e:
            logger.error(f"生成 ETag 失败: {e}")
            etag = f'"{media.hash}"'

        # 检查客户端是否有缓存（If-None-Match）
        if_none_match = request.headers.get("if-none-match")
        
        # 调试日志
        logger.info(f"媒体文件请求 - ID: {media_id}")
        logger.info(f"  ETag: {etag}")
        logger.info(f"  If-None-Match (from client): {if_none_match}")
        logger.info(f"  Match result: {if_none_match == etag if if_none_match else 'N/A'}")
        
        if if_none_match and if_none_match == etag:
            # 文件未修改，返回 304 Not Modified
            logger.info(f"[OK] 命中 ETag 缓存，返回 304 - ID: {media_id}")
            return Response(status_code=304, headers={"ETag": etag})

        # 设置响应头
        encoded_filename = urllib.parse.quote(file_hash.filename.encode('utf-8'))
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": file_hash.mime_type,
            "X-Content-Type-Options": "nosniff",
            "ETag": etag,
            # 设置缓存控制：公共缓存，最大缓存时间 7 天
            "Cache-Control": "public, max-age=604800, immutable"
        }
        if file_hash.mime_type in PREVIEWABLE_TYPES:
            headers["Content-Disposition"] = f'inline; filename*=UTF-8\'\'{encoded_filename}'
        else:
            headers["Content-Disposition"] = f'attachment; filename*=UTF-8\'\'{encoded_filename}'

        # 处理本地文件
        if file_path.exists():
            return await handle_local_file(file_path, file_hash.mime_type, file_hash.filename, range_header, headers)

        # 处理其他本地路径
        if file_hash.storage_path.startswith("local://"):
            local_path = file_hash.storage_path.replace("local://", "", 1)
            local_file_path = Path(local_path)
            if not local_file_path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            return await handle_local_file(local_file_path, file_hash.mime_type, file_hash.filename, range_header,
                                           headers)

        # 处理 S3 存储
        elif file_hash.storage_path.startswith("s3://"):
            return await handle_s3_streaming(
                s3_path=file_hash.storage_path,
                mime_type=file_hash.mime_type,
                filename=file_hash.filename,
                range_header=range_header,
                headers=headers,
                media_hash=media.hash
            )
        else:
            raise HTTPException(status_code=400, detail="不支持的存储类型")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误")
