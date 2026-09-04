"""
WordPress 导入 API 端点
"""

import os
import tempfile
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User
from shared.services.integrations.wordpress_import import WordPressImportService
from src.api.v2._helpers import _catch
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.unified_manager import get_db_session as get_async_db

router = APIRouter(tags=["wordpress-import"])


async def parse_wordpress_xml(
    file: UploadFile = File(...),
    current_user: User = Depends(jwt_required)
):
    """
    解析 WordPress XML 文件

    Args:
        file: 上传�?WXR 文件

    Returns:
        解析结果和统计信...
    """
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        # 解析文件
        from shared.services.integrations.wordpress_import import WordPressImportService
        importer = WordPressImportService()
        result = importer.parse_wxr_file(tmp_path)

        if not result['success']:
            return JSONResponse(
                status_code=400,
                content={
                    'success': False,
                    'error': result.get('error', '解析失败')
                }
            )

        return {
            'success': True,
            'data': result['data'],
            'stats': result['stats']
        }

    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/import")
@_catch
async def import_wordpress_data(
    file: UploadFile = File(...),
    user_mapping: Optional[str] = Form(None),
    download_media: bool = Form(False),
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    import json

    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        # 解析文件
        importer = WordPressImportService()
        parse_result = importer.parse_wxr_file(tmp_path)

        if not parse_result['success']:
            return JSONResponse(
                status_code=400,
                content={
                    'success': False,
                    'error': parse_result.get('error', '解析失败')
                }
            )

        # 解析用户映射
        mapping_dict = {}
        if user_mapping:
            try:
                mapping_dict = json.loads(user_mapping)
            except Exception:
                pass

        # 导入到数据库
        import_result = await importer.import_to_database(
            parsed_data=parse_result['data'],
            db_session=db,
            user_mapping=mapping_dict
        )

        # 如果需要，下载媒体文件
        if download_media and import_result['success']:
            media_list = parse_result['data'].get('media', [])
            if media_list:
                media_result = await importer.download_media_files(media_list)
                import_result['media_download'] = media_result

        # 生成导入报告
        report = importer.generate_import_report(import_result)
        import_result['report'] = report

        return import_result

    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
