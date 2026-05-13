"""
媒体封面上传 API
提供文章封面图片上传功能
"""
import logging

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from src.setting import app_config
from src.utils.upload.public_upload import FileProcessor, process_single_file

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media-cover"])


@router.post('/cover')
async def upload_cover(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    上传文章封面图片
    
    Args:
        request: FastAPI Request对象，包含上传的文件
        
    Returns:
        上传结果，包含封面URL
    """
    try:
        # 检查是否有文件上传
        form = await request.form()
        if 'cover_image' not in form:
            return JSONResponse({'code': 400, 'msg': '未上传文件'}, status_code=400)

        file: UploadFile = form['cover_image']

        # 检查文件名是否为空
        if not file or not file.filename:
            return JSONResponse({'code': 400, 'msg': '文件名为空'}, status_code=400)

        # 读取文件内容
        file_data = await file.read()

        # 使用FileProcessor处理文件，支持常见的图片格式，最大8MB
        processor = FileProcessor(
            current_user_obj.id,
            allowed_mimes={'image/jpeg', 'image/png', 'image/gif', 'image/webp'},
            allowed_size=8 * 1024 * 1024
        )

        # 验证并处理文件
        is_valid, validation_result = processor.validate_file(file_data, file.filename)

        if not is_valid:
            return JSONResponse({'code': 400, 'msg': validation_result}, status_code=400)

        # 计算文件哈希
        file_hash = processor.calculate_hash(file_data)

        # 处理文件并在数据库中创建记录
        try:
            result = process_single_file(processor, file_data, file.filename, db)
        except Exception as e:
            await db.rollback()
            import traceback
            traceback.print_exc()
            return JSONResponse({'code': 500, 'msg': '文件处理失败', 'error': str(e)}, status_code=500)

        if not result['success']:
            await db.rollback()
            return JSONResponse({'code': 500, 'msg': '文件处理失败', 'error': result['error']}, status_code=500)

        if result['success']:
            domain = app_config.domain
            # 确保domain以/结尾
            if not domain.endswith('/'):
                domain += '/'

            # 创建特殊URL用于访问缩略图
            thumbnail_url = domain + "thumbnail?data=" + result['hash']
            s_url = thumbnail_url

            if s_url:
                cover_url = "/s/" + s_url
                return JSONResponse({'code': 200, 'msg': '上传成功', 'data': cover_url})
            else:
                # 即使创建短链接失败，也返回文件哈希，让前端可以构造URL
                cover_url = "/thumbnail?data=" + result['hash']
                return JSONResponse({'code': 200, 'msg': '上传成功', 'data': cover_url})
        else:
            return JSONResponse({'code': 500, 'msg': '文件处理失败', 'error': result['error']}, status_code=500)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({'code': 500, 'msg': '上传失败', 'error': str(e)}, status_code=500)
