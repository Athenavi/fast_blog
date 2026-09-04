"""
图片编辑 API �?裁剪、旋转、滤�?"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.media import Media
from shared.services.media.image_tool.image_editor import ImageEditor
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.unified_logger import default_logger as logger
from src.utils.database.unified_manager import get_db_session as get_async_db

router = APIRouter(tags=["image-edit"])
editor = ImageEditor()
STORAGE_ROOT = Path("storage").resolve()


def _validate_file_path(file_path: str) -> Path:
    if not file_path:
        raise ValueError("文件路径为空")
    resolved = Path(file_path).resolve()
    try:
        resolved.relative_to(STORAGE_ROOT)
    except ValueError:
        raise ValueError(f"文件路径不在允许�?storage 目录范围...")
    if not resolved.exists():
        raise ValueError("文件不存...")
    return resolved


@router.get("/{media_id}/info")
async def get_image_info(
    media_id: int,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(jwt_required),
):
    try:
        result = await db.execute(select(Media).where(Media.id == media_id))
        media = result.scalar_one_or_none()
        if not media:
            return fail("媒体不存...")

        file_path = media.file_path or media.url or ""
        if not file_path:
            return fail("图片文件路径无效")

        validated_path = _validate_file_path(file_path)
        info = await asyncio.to_thread(editor.get_image_info, str(validated_path))
        return ok(data={"media_id": media_id, "filename": media.filename or media.title, "info": info})
    except ValueError as e:
        logger.error(f"图片信息获取失败: {e}")
        return fail("获取图片信息失败")
    except Exception as e:
        logger.error(f"图片信息获取异常: {e}")
        return fail("获取图片信息失败")


@router.post("/{media_id}/crop")
async def crop_image(
    media_id: int,
    x: int = Form(...), y: int = Form(...),
    width: int = Form(...), height: int = Form(...),
    db: AsyncSession = Depends(get_async_db),
    _=Depends(jwt_required),
):
    """裁剪图片"""
    try:
        result = await db.execute(select(Media).where(Media.id == media_id))
        media = result.scalar_one_or_none()
        if not media or not media.file_path:
            return fail("媒体不存...")

        validated_path = _validate_file_path(media.file_path)
        await asyncio.to_thread(editor.process_image, str(validated_path),
                                [{"type": "crop", "x": x, "y": y, "width": width, "height": height}])
        return ok(data={"message": "裁剪成功"})
    except ValueError as e:
        logger.error(f"裁剪失败: {e}")
        return fail("裁剪失败")
    except Exception as e:
        logger.error(f"裁剪异常: {e}")
        return fail("裁剪失败")


@router.post("/{media_id}/rotate")
async def rotate_image(
    media_id: int,
    degrees: float = Form(...),
    db: AsyncSession = Depends(get_async_db),
    _=Depends(jwt_required),
):
    """旋转图片"""
    try:
        result = await db.execute(select(Media).where(Media.id == media_id))
        media = result.scalar_one_or_none()
        if not media or not media.file_path:
            return fail("媒体不存...")

        validated_path = _validate_file_path(media.file_path)
        await asyncio.to_thread(editor.process_image, str(validated_path), [{"type": "rotate", "degrees": degrees}])
        return ok(data={"message": f"旋转 {degrees}° 成功"})
    except ValueError as e:
        logger.error(f"旋转失败: {e}")
        return fail("旋转失败")
    except Exception as e:
        logger.error(f"旋转异常: {e}")
        return fail("旋转失败")


@router.post("/{media_id}/filter")
async def filter_image(
    media_id: int,
    filter_type: str = Form(...),
    db: AsyncSession = Depends(get_async_db),
    _=Depends(jwt_required),
):
    """应用图片滤镜"""
    try:
        result = await db.execute(select(Media).where(Media.id == media_id))
        media = result.scalar_one_or_none()
        if not media or not media.file_path:
            return fail("媒体不存...")

        validated_path = _validate_file_path(media.file_path)
        await asyncio.to_thread(editor.process_image, str(validated_path), [{"type": "filter", "filter": filter_type}])
        return ok(data={"message": f"滤镜 {filter_type} 已应用"})
    except ValueError as e:
        logger.error(f"滤镜失败: {e}")
        return fail("滤镜应用失败")
    except Exception as e:
        logger.error(f"滤镜异常: {e}")
        return fail("滤镜应用失败")


@router.post("/{media_id}/grayscale")
async def grayscale_image(
    media_id: int,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(jwt_required),
):
    try:
        result = await db.execute(select(Media).where(Media.id == media_id))
        media = result.scalar_one_or_none()
        if not media or not media.file_path:
            return fail("媒体不存...")

        validated_path = _validate_file_path(media.file_path)
        await asyncio.to_thread(editor.process_image, str(validated_path), [{"type": "grayscale"}])
        return ok(data={"message": "已转为灰度图"})
    except ValueError as e:
        logger.error(f"灰度转换失败: {e}")
        return fail("灰度转换失败")
    except Exception as e:
        logger.error(f"灰度转换异常: {e}")
        return fail("灰度转换失败")
