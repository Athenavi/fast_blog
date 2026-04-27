"""
批量操作API
提供文章、用户、媒体等资源的批量操作功能
"""

from typing import List, Optional

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update

from src.utils.database.unified_manager import get_db_session
from shared.models.article import Article
from shared.models.media import Media
from shared.models.user import User
from src.api.v1.responses import ApiResponse

router = APIRouter(tags=["batch-operations"])


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[int]


class BatchUpdateStatusRequest(BaseModel):
    """批量更新状态请求"""
    ids: List[int]
    status: str  # published/draft/hidden


class BatchUpdateCategoryRequest(BaseModel):
    """批量更新分类请求"""
    ids: List[int]
    category_id: int


@router.post("/articles/batch-delete")
async def batch_delete_articles(request_data: BatchDeleteRequest, db: AsyncSession = Depends(get_db_session)):
    """
    批量删除文章
    
    Args:
        request_data: 包含文章ID列表的请求体
        
    Returns:
        删除结果统计
    """
    try:
        # 实现批量删除逻辑
        result = await db.execute(
            delete(Article).where(Article.id.in_(request_data.ids))
        )
        await db.commit()
        deleted_count = result.rowcount
        
        return ApiResponse(
            success=True,
            message=f"成功删除 {deleted_count} 篇文章",
            data={
                'deleted_count': deleted_count,
                'ids': request_data.ids
            }
        )
    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"批量删除失败: {str(e)}")


@router.post("/articles/batch-update-status")
async def batch_update_article_status(request_data: BatchUpdateStatusRequest,
                                      db: AsyncSession = Depends(get_db_session)):
    """
    批量更新文章状态
    
    Args:
        request_data: 包含ID列表和新状态的请求体
        
    Returns:
        更新结果统计
    """
    try:
        # 实现批量更新状态逻辑
        status_map = {'published': 1, 'draft': 0, 'hidden': 2}
        status_value = status_map.get(request_data.status, 1)

        result = await db.execute(
            update(Article)
            .where(Article.id.in_(request_data.ids))
            .values(status=status_value)
        )
        await db.commit()
        updated_count = result.rowcount
        
        return ApiResponse(
            success=True,
            message=f"成功更新 {updated_count} 篇文章的状态为 '{request_data.status}'",
            data={
                'updated_count': updated_count,
                'status': request_data.status,
                'ids': request_data.ids
            }
        )
    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"批量更新状态失败: {str(e)}")


@router.post("/articles/batch-update-category")
async def batch_update_article_category(request_data: BatchUpdateCategoryRequest,
                                        db: AsyncSession = Depends(get_db_session)):
    """
    批量更新文章分类
    
    Args:
        request_data: 包含ID列表和新分类ID的请求体
        
    Returns:
        更新结果统计
    """
    try:
        # 实现批量更新分类逻辑
        result = await db.execute(
            update(Article)
            .where(Article.id.in_(request_data.ids))
            .values(category_id=request_data.category_id)
        )
        await db.commit()
        updated_count = result.rowcount
        
        return ApiResponse(
            success=True,
            message=f"成功将 {updated_count} 篇文章分配到新分类",
            data={
                'updated_count': updated_count,
                'category_id': request_data.category_id,
                'ids': request_data.ids
            }
        )
    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"批量更新分类失败: {str(e)}")


@router.post("/users/batch-update-role")
async def batch_update_user_role(
    ids: List[int] = Body(...),
    role: str = Body(...),
        db: AsyncSession = Depends(get_db_session)
):
    """
    批量更新用户角色
    
    Args:
        ids: 用户ID列表
        role: 新角色
        
    Returns:
        更新结果统计
    """
    try:
        # 实现批量更新用户角色逻辑 - 更新is_superuser字段
        is_admin = role in ['admin', 'superuser']
        result = await db.execute(
            update(User)
            .where(User.id.in_(ids))
            .values(is_superuser=is_admin)
        )
        await db.commit()
        updated_count = result.rowcount
        
        return ApiResponse(
            success=True,
            message=f"成功更新 {updated_count} 个用户的角色为 '{role}'"
        )
    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"批量更新角色失败: {str(e)}")


@router.post("/media/batch-delete")
async def batch_delete_media(ids: List[int] = Body(...), db: AsyncSession = Depends(get_db_session)):
    """
    批量删除媒体文件
    
    Args:
        ids: 媒体ID列表
        
    Returns:
        删除结果统计
    """
    try:
        # 实现批量删除媒体逻辑
        result = await db.execute(
            delete(Media).where(Media.id.in_(ids))
        )
        await db.commit()
        deleted_count = result.rowcount
        
        return ApiResponse(
            success=True,
            message=f"成功删除 {deleted_count} 个媒体文件"
        )
    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"批量删除媒体失败: {str(e)}")


@router.post("/media/batch-move-folder")
async def batch_move_media_to_folder(
    ids: List[int] = Body(...),
    folder_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """
    批量移动媒体到文件夹
    
    Args:
        ids: 媒体ID列表
        folder_id: 目标文件夹ID(None表示根目录)
        
    Returns:
        移动结果统计
    """
    try:
        # 实现批量移动媒体逻辑
        updated_count = db.query(Media).filter(
            Media.id.in_(ids)
        ).update({Media.folder_id: folder_id}, synchronize_session=False)
        db.commit()
        
        return ApiResponse(
            success=True,
            message=f"成功移动 {updated_count} 个媒体文件"
        )
    except Exception as e:
        db.rollback()
        return ApiResponse(success=False, error=f"批量移动媒体失败: {str(e)}")
