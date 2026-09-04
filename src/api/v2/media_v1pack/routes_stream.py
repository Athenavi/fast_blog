"""
文件获取、流式传输、范围请�?"""
import urllib.parse
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.media import Media
from shared.models.media.file_hash import FileHash
from shared.utils.logger import get_logger
from src.api.v2._helpers import _catch
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.unified_manager import get_db_session as get_async_db
from .utils import PREVIEWABLE_TYPES, handle_local_file, handle_s3_streaming

logger = get_logger(__name__)
router = APIRouter()


async def get_cover_image(filename: str):
    """
    获取封面图片（公开访问，无需认证�?
    Args:
        filename: 封面文件名，格式�?{media_id}_{hash}.{ext}

    Returns:
        封面图片文件
    """
    # 构建封面文件路径
    cover_dir = Path("storage/cache/cover")

    # 防御路径遍历：确保文件名仅包含合法字�?    if not filename or '/' in filename or '\\' in filename or '..' in filename:
    raise HTTPException(status_code=403, detail="非法的文件路�?)
    cover_path = cover_dir / filename

    # 安全检查：防止目录遍历攻击
    if not cover_path.exists():
        raise HTTPException(status_code=404, detail="封面图片不存�?)

    # 确保文件在允许的目录�?    try:
        cover_path.resolve().relative_to(cover_dir.resolve())
    except ValueError:
raise HTTPException(status_code=403, detail="非法的文件路�?)

    # 确定 MIME 类型
    ext = cover_path.suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
    }
    content_type = mime_types.get(ext, 'image/jpeg')

    # 返回文件，设置缓存头
    return FileResponse(
        path=cover_path,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=604800, immutable",
            # 7天缓�?            "X-Content-Type-Options": "nosniff",
        }
    )



@router.head("/{media_id}")
@_catch
async def head_media_file_by_id(
        media_id: int,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """HEAD 请求 - 检查媒体文件是否存在（不返回内容）"""
    media_query = select(Media).where(Media.id == media_id)
    media_result = await db.execute(media_query)
    media = media_result.scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=404, detail="文件不存�?)

    if media.user != current_user_obj.id and not media.is_public:
            raise HTTPException(status_code=403, detail="无权访问该媒体文�?)

    return Response(status_code=200, headers={
        "Accept-Ranges": "bytes",
        "Content-Type": media.mime_type or 'application/octet-stream',
        "Content-Length": str(media.file_size or 0),
    })


@router.get("/{media_id}")
@_catch
async def get_media_file_by_id(
        media_id: int,
        request: Request,
        range_header: Optional[str] = None,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    # 查询媒体文件（支持访问自己的文件或公开文件�?    media_query = select(Media).where(Media.id == media_id)
    media_result = await db.execute(media_query)
    media = media_result.scalar_one_or_none()

    if not media:
        logger.error(f"媒体文件不存�?- ID: {media_id}")
        raise HTTPException(status_code=404, detail="文件不存�?)

        # 检查用户权限（只能访问自己的文件或公开文件�?    if media.user != current_user_obj.id and not media.is_public:
        raise HTTPException(status_code=403, detail="无权访问该媒体文�?)

    # 查询文件哈希信息
    file_hash_query = select(FileHash).where(FileHash.hash == media.hash)
    file_hash_result = await db.execute(file_hash_query)
    file_hash = file_hash_result.scalar_one_or_none()
    if not file_hash:
            raise HTTPException(status_code=404, detail="文件不存�?)

        # 确定文件路径（用于生�?ETag�?    # 注意：文件可能带扩展名或不带扩展名，需要尝试两种情�?    # 防御路径遍历：确�?hash 仅包含合法字�?    if not all(c.isalnum() or c in '-_' for c in media.hash):
        logger.error(f"非法文件hash: {media.hash}")
        raise HTTPException(status_code=404, detail="文件不存�?)
    file_path_without_ext = Path(f"storage/{media.hash[:2]}/{media.hash}")
    file_path_with_ext = Path(f"storage/{media.hash[:2]}/{media.hash}.png")  # 默认尝试 .png

        # 如果 storage_path 中有扩展名信息，使用�?    if file_hash.storage_path and '.' in Path(file_hash.storage_path).name:
        ext = Path(file_hash.storage_path).suffix
        file_path_with_ext = Path(f"storage/{media.hash[:2]}/{media.hash}{ext}")

    # 优先使用带扩展名的路径，如果不存在则使用不带扩展名的路径
    if file_path_with_ext.exists():
        file_path = file_path_with_ext
    elif file_path_without_ext.exists():
        file_path = file_path_without_ext
    else:
        file_path = file_path_without_ext  # 默认使用不带扩展名的路径

        # 生成 ETag：直接使用文件修改时�?    try:
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


# 检查客户端是否有缓存（If-None-Match�?    if_none_match = request.headers.get("if-none-match")

    if if_none_match and if_none_match == etag:
        # 文件未修改，返回 304 Not Modified
        logger.info(f"[OK] 命中 ETag 缓存，返�?304 - ID: {media_id}")
        return Response(status_code=304, headers={"ETag": etag})

# 设置响应�?    encoded_filename = urllib.parse.quote(file_hash.filename.encode('utf-8'))
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": file_hash.mime_type,
        "X-Content-Type-Options": "nosniff",
        "ETag": etag,
        # 设置缓存控制：公共缓存，最大缓存时�?7 �?        "Cache-Control": "public, max-age=604800, immutable"
    }
    if file_hash.mime_type in PREVIEWABLE_TYPES:
        headers["Content-Disposition"] = f'inline; filename*=UTF-8\'\'{encoded_filename}'
    else:
        headers["Content-Disposition"] = f'attachment; filename*=UTF-8\'\'{encoded_filename}'

        # 处理本地文件（优先检查标准路径，支持带扩展名和不带扩展名�?    if file_path.exists():
        logger.info("  [OK] 文件存在于标准路�?)
        return await handle_local_file(file_path, file_hash.mime_type, file_hash.filename, range_header, headers)

# 如果标准路径不存在，尝试�?storage_path 构建完整路径
    if file_hash.storage_path:
        # 处理相对路径格式：objects/xx/xxx.ext
        if not file_hash.storage_path.startswith(("s3://",)):
            # 防御路径遍历：标准化并验证前缀
            try:
                full_path = (Path("storage") / file_hash.storage_path).resolve()
                safe_storage = Path("storage").resolve()
                if not str(full_path).startswith(str(safe_storage)):
                    logger.error(f"storage_path 路径逃�? {file_hash.storage_path}")
                    raise HTTPException(status_code=403, detail="非法的文件路�?)
            except (ValueError, OSError, RuntimeError) as e:
                logger.error(f"storage_path 解析失败: {e}")
                raise HTTPException(status_code=403, detail="非法的文件路�?)
                logger.info("  尝试�?storage_path 构建路径")
            if full_path.exists():
                logger.info("  [OK] 文件存在�?storage_path 对应的路�?)
                return await handle_local_file(full_path, file_hash.mime_type, file_hash.filename, range_header,
                                               headers)

    # 处理 S3 存储
    elif file_hash.storage_path and file_hash.storage_path.startswith("s3://"):
        logger.info("  [OK] 使用 S3 路径")
        return await handle_s3_streaming(
            s3_path=file_hash.storage_path,
            mime_type=file_hash.mime_type,
            filename=file_hash.filename,
            range_header=range_header,
            headers=headers,
            media_hash=media.hash
        )
    else:
        # 如果 storage_path 为空或无效，但文件也不存在于标准路径
        logger.error(f"  [ERROR] 不支持的存储类型")
        logger.error("  文件不存在于标准路径�?storage_path")
        logger.error(f"  FileHash 摘要: id={file_hash.id}")

        # 如果文件实际上存在于标准路径但没有被检测到（可能是权限问题�?        if file_path.exists():
            logger.warning(f"  [WARN] 文件存在但之前的检查失败，重试...")
            return await handle_local_file(file_path, file_hash.mime_type, file_hash.filename, range_header,
                                           headers)

        raise HTTPException(status_code=400,
                            detail=f"不支持的存储类型: '{file_hash.storage_path}'，文件也不存在于标准路径")
