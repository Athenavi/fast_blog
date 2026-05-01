"""
批量操作 API
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.database import get_db
from shared.services.batch_operations import create_batch_service

router = APIRouter(prefix="/batch", tags=["batch"])


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[int]


class BatchUpdateStatusRequest(BaseModel):
    """批量更新状态请求"""
    ids: List[int]
    status: str


class BatchMoveCategoryRequest(BaseModel):
    """批量移动分类请求"""
    ids: List[int]
    category_id: int


class BatchAddTagsRequest(BaseModel):
    """批量添加标签请求"""
    ids: List[int]
    tags: List[str]


@router.post("/articles/delete")
async def batch_delete_articles(
        request: BatchDeleteRequest,
        operator_id: Optional[int] = Query(None, description="操作者ID"),
        db: AsyncSession = Depends(get_db)
):
    """
    批量删除文章
    
    Args:
        request: 删除请求
        operator_id: 操作者ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = create_batch_service(db)
        result = await service.batch_delete_articles(
            article_ids=request.ids,
            operator_id=operator_id
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/update-status")
async def batch_update_article_status(
        request: BatchUpdateStatusRequest,
        operator_id: Optional[int] = Query(None, description="操作者ID"),
        db: AsyncSession = Depends(get_db)
):
    """
    批量更新文章状态
    
    Args:
        request: 更新请求
        operator_id: 操作者ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = create_batch_service(db)
        result = await service.batch_update_article_status(
            article_ids=request.ids,
            status=request.status,
            operator_id=operator_id
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/move-category")
async def batch_move_to_category(
        request: BatchMoveCategoryRequest,
        operator_id: Optional[int] = Query(None, description="操作者ID"),
        db: AsyncSession = Depends(get_db)
):
    """
    批量移动文章到指定分类
    
    Args:
        request: 移动请求
        operator_id: 操作者ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = create_batch_service(db)
        result = await service.batch_move_to_category(
            article_ids=request.ids,
            category_id=request.category_id,
            operator_id=operator_id
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/add-tags")
async def batch_add_tags(
        request: BatchAddTagsRequest,
        operator_id: Optional[int] = Query(None, description="操作者ID"),
        db: AsyncSession = Depends(get_db)
):
    """
    批量添加标签
    
    Args:
        request: 添加标签请求
        operator_id: 操作者ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = create_batch_service(db)
        result = await service.batch_add_tags(
            article_ids=request.ids,
            tags=request.tags,
            operator_id=operator_id
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comments/delete")
async def batch_delete_comments(
        request: BatchDeleteRequest,
        operator_id: Optional[int] = Query(None, description="操作者ID"),
        db: AsyncSession = Depends(get_db)
):
    """
    批量删除评论
    
    Args:
        request: 删除请求
        operator_id: 操作者ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = create_batch_service(db)
        result = await service.batch_delete_comments(
            comment_ids=request.ids,
            operator_id=operator_id
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comments/update-status")
async def batch_update_comment_status(
        request: BatchUpdateStatusRequest,
        operator_id: Optional[int] = Query(None, description="操作者ID"),
        db: AsyncSession = Depends(get_db)
):
    """
    批量更新评论状态
    
    Args:
        request: 更新请求
        operator_id: 操作者ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = create_batch_service(db)
        result = await service.batch_update_comment_status(
            comment_ids=request.ids,
            status=request.status,
            operator_id=operator_id
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
