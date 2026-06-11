"""
媒体封面上传 API
提供文章封面图片上传功能
"""

from fastapi import APIRouter, Depends, Request, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from src.utils.upload.public_upload import FileProcessor, process_single_file

router = APIRouter(tags=["media-cover"])

from src.unified_logger import default_logger as logger

from functools import wraps
from src.api.v2._helpers import ok, fail


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[{func.__name__}] {e}")
            return fail(str(e))
    return wrapper


@router.post('/cover')
@_catch
async def upload_cover(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """上传文章封面图片"""
    form = await request.form()
    if 'cover_image' not in form:
        return JSONResponse({'code': 400, 'msg': '未上传文件'}, status_code=400)

    file: UploadFile = form['cover_image']
    if not file or not file.filename:
        return JSONResponse({'code': 400, 'msg': '文件名为空'}, status_code=400)

    file_data = await file.read()

    processor = FileProcessor(
        current_user_obj.id,
        allowed_mimes={'image/jpeg', 'image/png', 'image/gif', 'image/webp'},
        allowed_size=8 * 1024 * 1024
    )

    is_valid, validation_result = processor.validate_file(file_data, file.filename)
    if not is_valid:
        return JSONResponse({'code': 400, 'msg': validation_result}, status_code=400)

    try:
        result = await process_single_file(processor, file_data, file.filename, db)
    except Exception as e:
        await db.rollback()
        return JSONResponse({'code': 500, 'msg': '文件处理失败', 'error': str(e)}, status_code=500)

    if not result['success']:
        await db.rollback()
        return JSONResponse({'code': 500, 'msg': '文件处理失败', 'error': result['error']}, status_code=500)

    storage_path = result.get('storage_path', '')
    if storage_path:
        cover_url = f"/api/v2/assets/storage/{storage_path}"
    else:
        cover_url = f"/api/v2/media/{result.get('media_id', '')}"
    return JSONResponse({'code': 200, 'msg': '上传成功', 'data': cover_url})
