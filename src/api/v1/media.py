"""
媒体资源API - 处理媒体文件上传、管理和访问功能
"""
import logging
from threading import Thread

import humanize
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.utils.storage_utils import convert_storage_size, async_file_cleanup
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import cache
from src.extensions import get_async_db_session as get_async_db
from src.models import Media, FileHash
from src.models.user import User
from src.setting import AppConfig, BaseConfig, app_config
from src.utils.upload.public_upload import ChunkedUploadProcessor, FileProcessor, process_single_file

router = APIRouter(prefix="/media", tags=["media"])

base_dir = AppConfig.base_dir

logger = logging.getLogger(__name__)


async def get_user_storage_used(user_id: int, db: AsyncSession):
    """获取用户已使用的存储空间"""
    try:
        # 查询用户的所有媒体文件及其对应的文件大小
        storage_used_query = select(func.sum(FileHash.file_size)).join(
            Media, Media.hash == FileHash.hash
        ).where(
            Media.user_id == user_id
        )

        storage_used_result = await db.execute(storage_used_query)
        storage_used = storage_used_result.scalar() or 0

        logger.debug(f"用户 {user_id} 存储使用量: {storage_used} bytes")
        return int(storage_used)
    except Exception as e:
        logger.error(f"获取用户存储使用量失败: {str(e)}")
        return 0


@cache.memoize(60)
async def get_user_storage_limit(user_id: int, db: AsyncSession):
    """
    根据用户VIP等级获取存储限制
    普通用户: 512MB
    VIP 1级: 1GB
    VIP 2级: 5GB
    VIP 3级: 20GB
    """
    try:
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            logger.warning(f"未找到用户 {user_id}，使用默认存储限制")
            return BaseConfig.USER_FREE_STORAGE_LIMIT

        # 基础免费空间
        base_limit = BaseConfig.USER_FREE_STORAGE_LIMIT  # 512MB
        logger.debug(f"用户 {user_id} VIP等级: {user.vip_level}, 基础限制: {base_limit} bytes")

        # 根据VIP等级增加存储空间
        if user.vip_level == 1:
            storage_limit = base_limit * 2  # 1GB
        elif user.vip_level == 2:
            storage_limit = base_limit * 10  # 5GB
        elif user.vip_level >= 3:
            storage_limit = base_limit * 40  # 20GB
        else:
            storage_limit = base_limit  # 512MB for non-VIP users

        logger.debug(f"用户 {user_id} 最终存储限制: {storage_limit} bytes")
        return storage_limit
    except Exception as e:
        logger.error(f"获取用户存储限制失败: {str(e)}")
        return BaseConfig.USER_FREE_STORAGE_LIMIT


from sqlalchemy import case, func
from decimal import Decimal


@router.get("/")
async def get_user_media_api(
        current_user_obj=Depends(jwt_required),
        media_type: str = Query("all"),
        page: int = Query(1, ge=1),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户媒体文件列表API - 优化版
    """
    try:
        user_id = current_user_obj.id
        per_page = 20
        offset = (page - 1) * per_page

        # 1. 构建基础查询
        base_query = (
            select(Media)
            .join(FileHash, Media.hash == FileHash.hash)
            .where(Media.user_id == user_id)
        )

        # 2. 媒体类型筛选
        mime_type_filters = {
            'image': FileHash.mime_type.startswith('image'),
            'video': FileHash.mime_type.startswith('video'),
            'audio': FileHash.mime_type.startswith('audio'),
            'document': FileHash.mime_type.in_([
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'text/plain',
                'text/markdown'
            ]),
            'application/pdf': FileHash.mime_type == 'application/pdf',
            'application/zip': FileHash.mime_type.in_(['application/zip', 'application/x-rar-compressed'])
        }

        query = base_query
        if media_type != 'all' and media_type in mime_type_filters:
            query = query.where(mime_type_filters[media_type])

        # 3. 获取分页数据
        from sqlalchemy.orm import selectinload

        paginated_query = (
            query
            .options(selectinload(Media.file_hash))
            .order_by(Media.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )

        media_result = await db.execute(paginated_query)
        media_files = media_result.scalars().all()

        # 4. 获取总数
        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar() or 0

        # 5. 获取存储信息（可以并行执行这两个）
        storage_used_task = get_user_storage_used(user_id, db)
        storage_limit_task = get_user_storage_limit(user_id, db)

        storage_used, storage_total_bytes = await asyncio.gather(
            storage_used_task,
            storage_limit_task
        )
        storage_total_bytes = Decimal(str(storage_total_bytes))

        # 6. 构建统计查询（一次性获取所有统计数据）
        # 使用子查询避免重复扫描
        stats_subquery = (
            select(
                FileHash.mime_type,
                FileHash.file_size,
                Media.id
            )
            .join(Media, FileHash.hash == Media.hash)
            .where(Media.user_id == user_id)
            .subquery()
        )

        stats_query = select(
            func.count().label('total_count'),
            func.sum(
                case(
                    (stats_subquery.c.mime_type.startswith('image'), 1),
                    else_=0
                )
            ).label('image_count'),
            func.sum(
                case(
                    (stats_subquery.c.mime_type.startswith('video'), 1),
                    else_=0
                )
            ).label('video_count'),
            func.sum(
                case(
                    (stats_subquery.c.mime_type.startswith('audio'), 1),
                    else_=0
                )
            ).label('audio_count'),
            func.sum(
                case(
                    (stats_subquery.c.mime_type.in_([
                        'application/pdf',
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/vnd.ms-excel',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'application/vnd.ms-powerpoint',
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        'text/plain',
                        'text/markdown'
                    ]), 1),
                    else_=0
                )
            ).label('document_count')
        ).select_from(stats_subquery)

        stats_result = await db.execute(stats_query)
        stats_row = stats_result.first()

        # 7. 计算分页信息
        total_pages = max(1, (total + per_page - 1) // per_page)
        has_prev = page > 1
        has_next = page < total_pages

        # 8. 准备统计数据
        stats_data = {
            'image_count': int(stats_row.image_count or 0),
            'video_count': int(stats_row.video_count or 0),
            'audio_count': int(stats_row.audio_count or 0),
            'document_count': int(stats_row.document_count or 0),
            'storage_used': humanize.naturalsize(storage_used),
            'storage_total': convert_storage_size(storage_total_bytes),
            'storage_percentage': 0,
            'canBeUploaded': False,
            'totalUsed': storage_used
        }

        # 9. 计算存储百分比和上传权限
        if storage_total_bytes > 0:
            # 添加最小化处理，确保不超过100%
            storage_percentage = (storage_used / storage_total_bytes * 100)
            stats_data['storage_percentage'] = min(100, int(storage_percentage))
            stats_data['canBeUploaded'] = storage_total_bytes - storage_used > 1024
        else:
            logger.warning(f"用户 {user_id} 存储限制为0，设置使用百分比为0")

        logger.debug(f"用户 {user_id} 存储统计: {stats_data}")

        # 10. 构建响应数据
        media_items = [{
            'id': media_file.id,
            'original_filename': media_file.original_filename,
            'hash': media_file.hash,
            'mime_type': media_file.file_hash.mime_type,
            'file_size': media_file.file_hash.file_size,
            'created_at': media_file.created_at.isoformat() if media_file.created_at else None
        } for media_file in media_files]

        return {
            "success": True,
            "data": {
                "media_items": media_items,
                "users": [],
                "pagination": {
                    "current_page": page,
                    "pages": total_pages,
                    "total": total,
                    "has_prev": has_prev,
                    "has_next": has_next,
                    "per_page": per_page
                },
                "stats": stats_data
            }
        }

    except Exception as e:
        logger.error(f"获取用户媒体文件列表失败: {str(e)}", exc_info=True)
        return JSONResponse(
            {
                'success': False,
                'message': '获取媒体文件列表失败',
                'error': str(e)
            },
            status_code=500
        )


import asyncio
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, Response, Depends
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles
import aioboto3
from botocore.exceptions import ClientError
import tempfile

# 支持预览的MIME类型
PREVIEWABLE_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
    'video/mp4', 'video/webm', 'video/ogg',
    'audio/mpeg', 'audio/ogg', 'audio/wav',
    'application/pdf',
    'text/plain', 'text/html', 'text/css', 'text/javascript',
    'application/json'
}


@router.get("/{media_id}")
async def get_media_file_by_id(
        media_id: int,
        range_header: Optional[str] = None,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    通过ID获取媒体文件，支持流式传输和浏览器预览
    """
    try:
        # 1. 查询媒体文件记录
        media_query = select(Media).where(
            Media.id == media_id,
            Media.user_id == current_user_obj.id
        )
        media_result = await db.execute(media_query)
        media = media_result.scalar_one_or_none()

        if not media:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 2. 获取文件哈希记录
        file_hash_query = select(FileHash).where(FileHash.hash == media.hash)
        file_hash_result = await db.execute(file_hash_query)
        file_hash = file_hash_result.scalar_one_or_none()

        if not file_hash:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 3. 设置响应头，允许浏览器预览
        # 使用RFC 6266标准处理包含中文的文件名
        import urllib.parse
        encoded_filename = urllib.parse.quote(file_hash.filename.encode('utf-8'))
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename*=UTF-8\'\'{encoded_filename}',
            "Content-Type": file_hash.mime_type,
            "X-Content-Type-Options": "nosniff"
        }

        # 4. 如果是可预览的类型，添加预览相关头
        if file_hash.mime_type in PREVIEWABLE_TYPES:
            headers["Content-Disposition"] = f'inline; filename*=UTF-8\'\'{encoded_filename}'
        else:
            headers["Content-Disposition"] = f'attachment; filename*=UTF-8\'\'{encoded_filename}'

        # 5. 检查本地存储文件
        file_path = Path(f"storage/objects/{media.hash[:2]}/{media.hash}")
        if file_path.exists():
            return await handle_local_file(
                file_path=file_path,
                mime_type=file_hash.mime_type,
                filename=file_hash.filename,
                range_header=range_header,
                headers=headers
            )

        # 6. 处理不同存储类型
        if file_hash.storage_path.startswith("local://"):
            local_path = file_hash.storage_path.replace("local://", "", 1)
            local_file_path = Path(local_path)

            if not local_file_path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")

            return await handle_local_file(
                file_path=local_file_path,
                mime_type=file_hash.mime_type,
                filename=file_hash.filename,
                range_header=range_header,
                headers=headers
            )

        elif file_hash.storage_path.startswith("s3://"):
            # 7. 处理S3文件 - 流式传输
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
        logger.error(f"获取媒体文件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def handle_local_file(
        file_path: Path,
        mime_type: str,
        filename: str,
        range_header: Optional[str],
        headers: dict
) -> Response:
    """
    处理本地文件，支持范围请求
    """
    file_size = file_path.stat().st_size

    if range_header:
        # 处理范围请求（支持视频/音频跳转）
        return await handle_range_request(file_path, range_header, file_size, mime_type, headers)
    else:
        # 完整文件响应
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=filename,
            headers=headers
        )


async def handle_range_request(
        file_path: Path,
        range_header: str,
        file_size: int,
        mime_type: str,
        headers: dict
) -> Response:
    """
    处理HTTP范围请求（用于视频/音频跳转）
    """
    range_bytes = range_header.replace("bytes=", "").split("-")
    start = int(range_bytes[0]) if range_bytes[0] else 0
    end = int(range_bytes[1]) if range_bytes[1] else file_size - 1

    if end >= file_size:
        end = file_size - 1

    content_length = end - start + 1
    headers.update({
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str(content_length)
    })

    async def file_iterator():
        async with aiofiles.open(file_path, 'rb') as f:
            await f.seek(start)
            remaining = content_length
            chunk_size = 8192

            while remaining > 0:
                read_size = min(chunk_size, remaining)
                chunk = await f.read(read_size)
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    return StreamingResponse(
        file_iterator(),
        status_code=206,  # Partial Content
        media_type=mime_type,
        headers=headers
    )


async def handle_s3_streaming(
        s3_path: str,
        mime_type: str,
        filename: str,
        range_header: Optional[str],
        headers: dict,
        media_hash: str
) -> Response:
    """
    处理S3文件的流式传输，支持范围请求
    """
    # 解析S3路径
    s3_url = s3_path.replace("s3://", "")
    bucket_key_parts = s3_url.split("/", 1)

    if len(bucket_key_parts) != 2:
        raise HTTPException(status_code=400, detail="无效的S3路径")

    bucket_name, object_key = bucket_key_parts

    # 检查缓存
    cache_path = Path(f"cache/objects/{media_hash}")
    if cache_path.exists() and not range_header:
        # 如果缓存存在且不是范围请求，使用缓存
        return await handle_local_file(
            file_path=cache_path,
            mime_type=mime_type,
            filename=filename,
            range_header=range_header,
            headers=headers
        )

    if range_header:
        # S3范围请求
        return await stream_s3_range(
            bucket_name=bucket_name,
            object_key=object_key,
            mime_type=mime_type,
            range_header=range_header,
            headers=headers
        )
    else:
        # S3完整文件流式传输（同时缓存）
        return await stream_and_cache_s3(
            bucket_name=bucket_name,
            object_key=object_key,
            mime_type=mime_type,
            filename=filename,
            headers=headers,
            cache_path=cache_path
        )


async def stream_s3_range(
        bucket_name: str,
        object_key: str,
        mime_type: str,
        range_header: str,
        headers: dict
) -> Response:
    """
    从S3流式传输特定范围的数据
    """
    try:
        session = aioboto3.Session()
        async with session.client('s3') as s3_client:
            # 获取文件大小
            head_response = await s3_client.head_object(
                Bucket=bucket_name,
                Key=object_key
            )
            file_size = head_response['ContentLength']

            # 解析范围
            range_bytes = range_header.replace("bytes=", "").split("-")
            start = int(range_bytes[0]) if range_bytes[0] else 0
            end = int(range_bytes[1]) if range_bytes[1] else file_size - 1

            if end >= file_size:
                end = file_size - 1

            content_length = end - start + 1
            range_str = f"bytes={start}-{end}"

            headers.update({
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length)
            })

            # 获取S3对象
            response = await s3_client.get_object(
                Bucket=bucket_name,
                Key=object_key,
                Range=range_str
            )

            async def s3_stream_iterator():
                async with response['Body'] as stream:
                    async for chunk in stream.iter_chunks(chunk_size=8192):
                        yield chunk

            return StreamingResponse(
                s3_stream_iterator(),
                status_code=206,
                media_type=mime_type,
                headers=headers
            )

    except ClientError as e:
        logger.error(f"S3范围请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文件获取失败")
    except Exception as e:
        logger.error(f"S3流式传输失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def stream_and_cache_s3(
        bucket_name: str,
        object_key: str,
        mime_type: str,
        filename: str,
        headers: dict,
        cache_path: Path
) -> Response:
    """
    从S3流式传输并同时缓存文件
    """
    # 创建缓存目录
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # 创建临时文件用于缓存
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=cache_path.parent)
    temp_path = Path(temp_file.name)

    try:
        # 构建S3配置
        s3_config = {
            'endpoint_url': getattr(app_config, 'S3_ENDPOINT_URL', None),
            'aws_access_key_id': getattr(app_config, 'S3_ACCESS_KEY', None),
            'aws_secret_access_key': getattr(app_config, 'S3_SECRET_KEY', None),
            'region_name': getattr(app_config, 'S3_REGION', 'us-east-1'),
            'use_ssl': getattr(app_config, 'S3_USE_SSL', True)
        }
        # 移除None值
        s3_config = {k: v for k, v in s3_config.items() if v is not None}
        
        session = aioboto3.Session()
        async with session.client('s3', **s3_config) as s3_client:
            # 获取S3对象
            response = await s3_client.get_object(
                Bucket=bucket_name,
                Key=object_key
            )

            file_size = response['ContentLength']
            headers["Content-Length"] = str(file_size)

            async def s3_stream_and_cache_iterator():
                total_bytes = 0
                try:
                    async with aiofiles.open(temp_path, 'wb') as cache_file:
                        async with response['Body'] as stream:
                            async for chunk in stream.iter_chunks(chunk_size=8192):
                                yield chunk
                                await cache_file.write(chunk)
                                total_bytes += len(chunk)

                    # 文件传输完成，重命名临时文件
                    if total_bytes == file_size:
                        temp_path.rename(cache_path)
                        logger.info(f"文件已缓存: {cache_path}")
                    else:
                        logger.warning(f"文件大小不匹配: 期望{file_size}, 实际{total_bytes}")

                except Exception as e:
                    logger.error(f"流式传输/缓存失败: {str(e)}")
                    # 清理临时文件
                    if temp_path.exists():
                        temp_path.unlink()
                    raise

            return StreamingResponse(
                s3_stream_and_cache_iterator(),
                media_type=mime_type,
                headers=headers
            )

    except ClientError as e:
        logger.error(f"S3获取失败: {str(e)}")
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail="文件获取失败")
    except Exception as e:
        logger.error(f"S3流式传输失败: {str(e)}")
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail="服务器内部错误")


# 移除不再需要的旧函数
# async def handle_s3_download, wait_for_download_completion,
# download_s3_file, background_s3_download, validate_and_move_file,
# verify_file_hash, cleanup_temp_files 等函数可以移除


@router.delete("/")
async def delete_user_media_api(
        current_user_obj=Depends(jwt_required),
        file_id_list: str = Query(..., alias="file-id-list"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除用户媒体文件API
    """
    try:
        if not file_id_list:
            return JSONResponse({'success': False, 'message': '缺少文件ID列表', 'error': '缺少文件ID列表'},
                                status_code=400)

        try:
            id_list = [int(media_id) for media_id in file_id_list.split(',')]
        except ValueError:
            return JSONResponse({'success': False, 'message': '文件ID包含非法字符', 'error': '文件ID包含非法字符'},
                                status_code=400)

        try:
            from sqlalchemy import select
            # 使用 with_for_update 锁定记录，避免并发问题
            target_files_query = select(Media).where(
                Media.id.in_(id_list),
                Media.user_id == current_user_obj.id
            )
            target_files_result = await db.execute(target_files_query)
            target_files = target_files_result.scalars().all()

            if len(target_files) != len(id_list):
                return JSONResponse({
                    'success': False,
                    'message': f'找到{len(target_files)}个文件，请求{len(id_list)}个',
                    'error': '可能文件不存在或无权访问'
                }, status_code=403)

            # 收集需要清理的信息
            cleanup_data = []
            media_hashes = []  # 收集所有涉及的hash
            valid_target_files = []  # 只处理hash为null的记录

            # 第一步：先检查所有记录的hash是否有效，过滤掉hash为null的记录
            for media_file in target_files:
                if media_file.hash is not None:
                    media_hashes.append(media_file.hash)
                    valid_target_files.append(media_file)
                else:
                    print(f"跳过hash为null的媒体记录: ID={media_file.id}")

            # 如果没有有效的记录，直接返回
            if not valid_target_files:
                return JSONResponse(
                    {'success': False, 'message': '没有有效的媒体记录可删除', 'error': '没有有效的媒体记录可删除'},
                    status_code=400)

            # 第二步：批量查询FileHash对象，确保它们属于当前会话
            from sqlalchemy import select
            file_hashes_query = select(FileHash).where(
                FileHash.hash.in_(media_hashes)
            )
            file_hashes_result = await db.execute(file_hashes_query)
            file_hashes = file_hashes_result.scalars().all()

            # 创建hash到对象的映射
            file_hash_map = {fh.hash: fh for fh in file_hashes}

            # 第三步：执行删除和更新操作
            for media_file in valid_target_files:
                await db.delete(media_file)

                file_hash_obj = file_hash_map.get(media_file.hash)
                if file_hash_obj:
                    file_hash_obj.reference_count -= 1
                    if file_hash_obj.reference_count == 0:
                        cleanup_data.append({
                            'hash': file_hash_obj.hash,
                            'storage_path': file_hash_obj.storage_path
                        })
                        await db.delete(file_hash_obj)

            # 提交所有更改
            await db.commit()

            # 启动后台清理
            if cleanup_data:
                Thread(target=async_file_cleanup,
                       args=(db, cleanup_data)).start()

            return JSONResponse({
                'success': True,
                'data': {
                    'deleted_count': len(valid_target_files),
                },
                'message': "删除成功，后台清理中"
            })

        except Exception as e:
            if db is not None:
                await db.rollback()
            print(f"删除失败: {str(e)}")
            return JSONResponse({'success': False, 'message': '数据库操作失败', 'error': '数据库操作失败'},
                                status_code=500)

    except Exception as e:
        print(f"请求处理异常: {str(e)}")
        return JSONResponse({'success': False, 'message': '服务器内部错误', 'error': '服务器内部错误'}, status_code=500)


# 媒体上传路由
@router.post("/upload")
async def upload_media_file(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """上传媒体文件"""
    try:
        # 使用默认的上传限制
        try:
            upload_limit = getattr(app_config, 'UPLOAD_LIMIT', 10 * 1024 * 1024)  # 默认10MB
            allowed_mimes = getattr(app_config, 'ALLOWED_MIMES',
                                    ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
                                     'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/x-flv',
                                     'video/webm', 'video/avi', 'video/msvideo', 'video/x-ms-wmv'])
        except Exception:
            upload_limit = 10 * 1024 * 1024  # 10MB
            allowed_mimes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
                             'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/x-flv',
                             'video/webm', 'video/avi', 'video/msvideo', 'video/x-ms-wmv']

        # 获取上传的文件
        form = await request.form()
        files = form.getlist('file')

        # 添加调试日志
        logger.info(f"接收到表单字段: {list(form.keys())}")
        logger.info(f"接收到文件数量: {len(files)}")

        for i, file in enumerate(files):
            logger.info(f"文件 {i}: 类型={type(file)}, filename={getattr(file, 'filename', 'N/A')}")

        if not files:
            return JSONResponse(
                {'success': False, 'message': '未找到上传的文件', 'error': 'no files uploaded'},
                status_code=400
            )

        # 处理多个文件上传
        results = []
        for file in files:
            # 检查是否为上传文件对象（兼容starlette和fastapi的UploadFile）
            if hasattr(file, 'filename') and hasattr(file, 'read'):
                try:
                    file_data = await file.read()
                    result = await _process_single_file_for_fastapi(
                        current_user_obj.id,
                        file_data,
                        file.filename,
                        upload_limit,
                        allowed_mimes,
                        db
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"处理文件 {getattr(file, 'filename', 'unknown')} 失败: {str(e)}")
                    results.append({'success': False, 'error': str(e)})
            else:
                logger.warning(f"跳过的非UploadFile对象: {type(file)}")

        # 检查结果
        successful_uploads = [r for r in results if r.get('success')]
        if successful_uploads:
            return JSONResponse({
                'success': True,
                'message': '上传成功',
                'data': {'files': successful_uploads}
            })
        else:
            # 收集所有错误信息
            error_messages = []
            for result in results:
                if not result.get('success'):
                    error_msg = result.get('error', '未知错误')
                    error_messages.append(error_msg)

            error_msg = '上传失败: ' + '; '.join(error_messages) if error_messages else '上传失败'
            return JSONResponse(
                {'success': False, 'message': '文件上传失败', 'error': error_msg},
                status_code=400
            )

    except Exception as e:
        logger.error(f"上传媒体文件错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            {'success': False, 'message': '服务器内部错误', 'error': str(e)},
            status_code=500
        )


async def _process_single_file_for_fastapi(
        user_id: int,
        file_data: bytes,
        filename: str,
        allowed_size: int,
        allowed_mimes: list,
        db: AsyncSession = Depends(get_async_db)
) -> dict:
    """FastAPI兼容的单文件处理函数"""
    # 转换MIME类型为集合
    if allowed_mimes and isinstance(allowed_mimes, list):
        allowed_mimes_set = set(str(mime) for mime in allowed_mimes)
    else:
        allowed_mimes_set = {
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
            'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/x-flv',
            'video/webm', 'video/avi', 'video/msvideo', 'video/x-ms-wmv',
            'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/flac', 'audio/aac', 'audio/mp4'
        }

    processor = FileProcessor(
        user_id,
        allowed_mimes=allowed_mimes_set,
        allowed_size=allowed_size
    )

    # 验证文件
    is_valid, validation_result = processor.validate_file(file_data, filename)
    if not is_valid:
        return {'success': False, 'error': validation_result}

    # 处理文件
    try:
        result = await process_single_file(processor, file_data, filename, db)
        return result
    except Exception as e:
        logger.error(f"文件处理失败: {str(e)}")
        return {'success': False, 'error': str(e)}


# 大文件分块上传路由
@router.post('/upload/chunked/init')
async def chunked_upload_init(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """初始化分块上传"""
    try:
        data = await request.json()
        filename = data.get('filename')
        total_size = data.get('total_size')
        total_chunks = data.get('total_chunks')
        file_hash = data.get('file_hash')  # 可选，用于秒传
        existing_upload_id = data.get('existing_upload_id')  # 可选，用于断点续传

        if not all([filename, total_size, total_chunks]):
            return JSONResponse(
                {'success': False, 'error': '缺少必要参数'},
                status_code=400
            )

        processor = ChunkedUploadProcessor(current_user_obj.id)
        result = await processor.init_upload(
            filename, total_size, total_chunks, file_hash, existing_upload_id, db
        )

        status_code = 200 if result.get('success') else 400
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        logger.error(f"初始化分块上传失败: {str(e)}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@router.post('/upload/chunked/chunk')
async def chunked_upload_chunk(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """上传分块"""
    import hashlib

    try:
        form = await request.form()
        upload_id = form.get('upload_id')
        chunk_index_str = form.get('chunk_index')
        chunk_hash = form.get('chunk_hash')

        # 添加调试日志
        logger.debug(
            f"收到的表单数据: upload_id={upload_id}, chunk_index_str={chunk_index_str}, chunk_hash={chunk_hash}")
        logger.debug(f"表单字段列表: {list(form.keys())}")

        # 详细记录每个字段的信息
        for key, value in form.items():
            logger.debug(f"表单字段 {key}: 类型={type(value)}, 值={repr(value)[:100]}")

        # 验证必要参数
        if not upload_id:
            return JSONResponse(
                {'success': False, 'error': '缺少upload_id'},
                status_code=400
            )

        if chunk_index_str is None:
            return JSONResponse(
                {'success': False, 'error': '缺少chunk_index'},
                status_code=400
            )

        try:
            chunk_index = int(chunk_index_str)
        except (ValueError, TypeError):
            return JSONResponse(
                {'success': False, 'error': 'chunk_index必须是有效的数字'},
                status_code=400
            )

        if not chunk_hash:
            return JSONResponse(
                {'success': False, 'error': '缺少chunk_hash'},
                status_code=400
            )

        # 获取分块数据
        chunk_data = None
        if 'chunk' in form:
            chunk_item = form.get('chunk')
            logger.debug(f"chunk_item 类型: {type(chunk_item)}")
            logger.debug(f"chunk_item 值: {repr(chunk_item)[:200] if chunk_item else 'None'}")

            # 添加更多调试信息
            logger.debug(f"form keys: {list(form.keys())}")
            for key, value in form.items():
                logger.debug(f"form[{key}] type: {type(value)}, value: {repr(value)[:100]}")

            if hasattr(chunk_item, 'file'):  # UploadFile 对象
                logger.debug("检测到 UploadFile 对象")
                chunk_data = await chunk_item.read()
            elif hasattr(chunk_item, 'read'):  # 文件类对象
                logger.debug("检测到有 read 方法的对象")
                chunk_data = await chunk_item.read()
            elif isinstance(chunk_item, bytes):  # 字节数据
                logger.debug("检测到字节数据")
                chunk_data = chunk_item
            elif isinstance(chunk_item, str):  # 字符串数据
                logger.debug("检测到字符串数据")
                try:
                    chunk_data = chunk_item.encode('utf-8')
                except Exception as e:
                    logger.error(f"字符串编码失败: {e}")
                    return JSONResponse(
                        {'success': False, 'error': '无效的分块数据格式'},
                        status_code=400
                    )
            elif chunk_item is not None:
                # 尝试转换为字节
                logger.debug(f"尝试转换其他类型: {type(chunk_item)}")
                try:
                    if hasattr(chunk_item, 'encode'):
                        chunk_data = chunk_item.encode()
                    else:
                        chunk_data = str(chunk_item).encode()
                except Exception as e:
                    logger.error(f"转换chunk数据失败: {e}")
                    return JSONResponse(
                        {'success': False, 'error': '无效的分块数据格式'},
                        status_code=400
                    )
            else:
                logger.debug("chunk_item 为 None")

        if chunk_data is None:
            # 如果没有找到chunk字段，尝试从body读取
            chunk_data = await request.body()

        if not chunk_data:
            return JSONResponse(
                {'success': False, 'error': '分块数据为空'},
                status_code=400
            )

        # 验证分块哈希
        actual_chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        if actual_chunk_hash != chunk_hash:
            return JSONResponse(
                {'success': False, 'error': '分块哈希验证失败'},
                status_code=400
            )

        processor = ChunkedUploadProcessor(current_user_obj.id)
        result = await processor.upload_chunk(upload_id, chunk_index, chunk_data, chunk_hash, db)

        status_code = 200 if result.get('success') else 400
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        logger.error(f"上传分块失败: {str(e)}", exc_info=True)
        return JSONResponse(
            {'success': False, 'error': f'服务器内部错误: {str(e)}'},
            status_code=500
        )


@router.post('/upload/chunked/complete')
async def chunked_upload_complete(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """完成分块上传"""
    try:
        data = await request.json()
        upload_id = data.get('upload_id')
        file_hash = data.get('file_hash')
        mime_type = data.get('mime_type')

        if not all([upload_id, file_hash, mime_type]):
            return JSONResponse(
                {'success': False, 'error': '缺少必要参数'},
                status_code=400
            )

        processor = ChunkedUploadProcessor(current_user_obj.id)
        result = await processor.complete_upload(upload_id, file_hash, mime_type, db)

        status_code = 200 if result.get('success') else 400
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        logger.error(f"完成分块上传失败: {str(e)}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@router.get('/upload/chunked/progress')
async def chunked_upload_progress(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取上传进度"""
    try:
        upload_id = request.query_params.get('upload_id')
        if not upload_id:
            return JSONResponse(
                {'success': False, 'error': '缺少upload_id'},
                status_code=400
            )

        processor = ChunkedUploadProcessor(current_user_obj.id)
        result = await processor.get_upload_progress(upload_id, db)

        status_code = 200 if result.get('success') else 400
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        logger.error(f"获取上传进度失败: {str(e)}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@router.get('/upload/chunked/chunks')
async def chunked_upload_chunks(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取已上传分块列表"""
    try:
        upload_id = request.query_params.get('upload_id')
        if not upload_id:
            return JSONResponse(
                {'success': False, 'error': '缺少upload_id'},
                status_code=400
            )

        processor = ChunkedUploadProcessor(current_user_obj.id)
        result = await processor.get_uploaded_chunks(upload_id, db)

        status_code = 200 if result.get('success') else 400
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        logger.error(f"获取已上传分块列表失败: {str(e)}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@router.post('/upload/chunked/cancel')
async def chunked_upload_cancel(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """取消上传任务"""
    try:
        data = await request.json()
        upload_id = data.get('upload_id')

        if not upload_id:
            return JSONResponse(
                {'success': False, 'error': '缺少upload_id'},
                status_code=400
            )

        processor = ChunkedUploadProcessor(current_user_obj.id)
        result = await processor.cancel_upload(upload_id, db)

        status_code = 200 if result.get('success') else 400
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        logger.error(f"取消上传任务失败: {str(e)}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )
