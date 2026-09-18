"""mobile/media：移动端图片与文章封面上传

路由前缀：``/api/v3/mobile/media``

复用 ``modules/content/media`` 的 ``media_service.upload_files``（同一套
``FileProcessor.validate_file`` 类型/大小校验 + ``process_single_file`` 落盘），
因此移动端与后台的上传行为一致。

范围说明：legacy 移动端上传里有一段图片压缩处理（依赖 PIL），本次**未迁移**——
它属于上传优化而非功能必需，且需要单独确认压缩参数与目标目录，记入二期。
"""

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import DBSession
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.content.media.service import media_service
from src.auth.auth_deps import jwt_required_dependency

router = APIRouter(prefix="/media", tags=["mobile-media"])


async def _store(current, db: DBSession, file: UploadFile) -> dict:
    if file is None or not file.filename:
        raise BadRequestError("未找到上传的文件")
    results = await media_service.upload_files(
        db, user_id=current.id, files=[(file.filename, await file.read())]
    )
    return results[0] if results else {}


@router.post("/upload/image", response_model=ResponseModel, summary="上传图片（需登录）")
async def upload_image(
    db: DBSession,
    user=Depends(jwt_required_dependency),
    file: UploadFile = File(...),
) -> dict:
    return resp.success(await _store(user, db, file), msg="上传成功")


@router.post("/upload/article-cover", response_model=ResponseModel, summary="上传文章封面（需登录）")
async def upload_article_cover(
    db: DBSession,
    user=Depends(jwt_required_dependency),
    file: UploadFile = File(...),
) -> dict:
    """与 ``/upload/image`` 同一实现，语义别名（移动端封面场景）"""
    return resp.success(await _store(user, db, file), msg="上传成功")
