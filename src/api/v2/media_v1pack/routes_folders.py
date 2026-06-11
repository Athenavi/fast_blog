"""
媒体文件夹 API 路由
提供文件夹的 CRUD 操作和媒体文件管理
"""

from functools import wraps
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Body, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.media.media_manager import media_folder_service
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["media-folders"])
from src.unified_logger import default_logger as logger


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


# ---------- 获取文件夹树 ----------
@router.get("/tree")
@_catch
async def get_folder_tree(
    include_media_count: bool = Query(True, description="是否包含媒体数量"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取文件夹树形结构
    
    Returns:
        文件夹树形结构列表
    """
    tree = await media_folder_service.get_folder_tree(
        db,
        current_user.id,
        include_media_count
    )
    return ok(data={"tree": tree})


# ---------- 获取文件夹列表 ----------
@router.get("/list")
@_catch
async def get_folder_list(
    parent_id: Optional[int] = Query(None, description="父文件夹ID，None表示根目录"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取文件夹列表（扁平结构）
    
    Args:
        parent_id: 父文件夹ID
        
    Returns:
        文件夹列表
    """
    folders = await media_folder_service.get_folder_list(
        db,
        current_user.id,
        parent_id
    )
    return ok(data={"folders": folders, "count": len(folders)})


# ---------- 获取文件夹详情 ----------
@router.get("/{folder_id}")
@_catch
async def get_folder_detail(
    folder_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取文件夹详情
    
    Args:
        folder_id: 文件夹ID
        
    Returns:
        文件夹详情
    """
    folder = await media_folder_service.get_folder_detail(
        db,
        folder_id,
        current_user.id
    )
    
    if not folder:
        return fail("文件夹不存在或无权访问")
    
    return ok(data=folder)


# ---------- 创建文件夹 ----------
@router.post("/")
@_catch
async def create_folder(
    request: Request,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    创建新文件夹
    
    Request Body:
        name: 文件夹名称（必填）
        parent_id: 父文件夹ID（可选）
        description: 描述（可选）
        is_public: 是否公开（可选，默认True）
    """
    body = await request.json()
    name = body.get('name')
    
    if not name:
        return fail("文件夹名称不能为空")
    
    result = await media_folder_service.create_folder(
        db,
        current_user.id,
        name=name,
        parent_id=body.get('parent_id'),
        description=body.get('description', ''),
        is_public=body.get('is_public', True)
    )
    
    if result['success']:
        return ok(message="文件夹创建成功", data=result['folder'])
    else:
        return fail(result['error'])


# ---------- 更新文件夹 ----------
@router.put("/{folder_id}")
@_catch
async def update_folder(
    folder_id: int,
    request: Request,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    更新文件夹信息
    
    Args:
        folder_id: 文件夹ID
        
    Request Body:
        name: 文件夹名称（可选）
        description: 描述（可选）
        is_public: 是否公开（可选）
        sort_order: 排序顺序（可选）
    """
    body = await request.json()
    
    result = await media_folder_service.update_folder(
        db,
        folder_id,
        current_user.id,
        **body
    )
    
    if result['success']:
        return ok(message="文件夹更新成功", data=result['folder'])
    else:
        return fail(result['error'])


# ---------- 删除文件夹 ----------
@router.delete("/{folder_id}")
@_catch
async def delete_folder(
    folder_id: int,
    delete_media: bool = Query(False, description="是否同时删除文件夹内的媒体文件"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    删除文件夹
    
    Args:
        folder_id: 文件夹ID
        delete_media: 是否同时删除媒体文件
        
    Note:
        - 如果文件夹包含子文件夹，必须先删除子文件夹
        - 如果不删除媒体文件，媒体将被移动到根目录
    """
    result = await media_folder_service.delete_folder(
        db,
        folder_id,
        current_user.id,
        delete_media
    )
    
    if result['success']:
        return ok(message=result['message'])
    else:
        return fail(result['error'])


# ---------- 移动媒体到文件夹 ----------
@router.post("/move-media")
@_catch
async def move_media_to_folder(
    media_ids: List[int] = Body(..., description="媒体文件ID列表"),
    folder_path: Optional[str] = Body(None, description="目标文件夹路径（如 folder1/folder2），None表示移动到根目录"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    批量移动媒体文件到文件夹
    
    Args:
        media_ids: 媒体文件ID列表
        folder_path: 目标文件夹路径（支持多级，如 "Photos/2024"）
    """
    if not media_ids:
        return fail("请选择要移动的文件")
    
    # 如果指定了文件夹路径，需要查找最终的文件夹ID
    target_folder_id = None
    if folder_path:
        from urllib.parse import unquote
        from shared.models import MediaFolder
        
        # 解码 URL 编码的路径
        decoded_path = unquote(folder_path)
        
        # 分割路径
        path_parts = [p.strip() for p in decoded_path.split('/') if p.strip()]
        
        if path_parts:
            # 逐级查找文件夹
            current_parent_id = None
            
            for i, part_name in enumerate(path_parts):
                folder_query = select(MediaFolder.id).where(
                    MediaFolder.name == part_name,
                    MediaFolder.user == current_user.id,
                    MediaFolder.parent_id == current_parent_id
                )
                folder_result = await db.execute(folder_query)
                folder_id = folder_result.scalar_one_or_none()
                
                if not folder_id:
                    return fail(f"文件夹路径不存在: {decoded_path}")
                
                # 如果是最后一级，记录目标文件夹 ID
                if i == len(path_parts) - 1:
                    target_folder_id = folder_id
                else:
                    # 否则继续查找下一级
                    current_parent_id = folder_id
    
    result = await media_folder_service.move_media_to_folder(
        db,
        media_ids,
        target_folder_id,
        current_user.id
    )
    
    if result['success']:
        return ok(message=result['message'], data={"moved_count": result['moved_count']})
    else:
        return fail(result['error'])


# ---------- 复制媒体到文件夹 ----------
@router.post("/copy-media")
@_catch
async def copy_media_to_folder(
    media_ids: List[int] = Body(..., description="媒体文件ID列表"),
    folder_id: Optional[int] = Body(None, description="目标文件夹ID"),
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    批量复制媒体文件到文件夹
    
    Args:
        media_ids: 媒体文件ID列表
        folder_id: 目标文件夹ID
        
    Note:
        目前实现为逻辑复制（改变folder_id），物理复制需要额外实现
    """
    if not media_ids:
        return fail("请选择要复制的文件")
    
    result = await media_folder_service.copy_media_to_folder(
        db,
        media_ids,
        folder_id,
        current_user.id
    )
    
    if result['success']:
        return ok(message=result['message'], data={"copied_count": result['moved_count']})
    else:
        return fail(result['error'])
