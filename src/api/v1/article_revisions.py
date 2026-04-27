"""
文章修订历史API端点
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.article_manager import compare_revisions, get_article_revisions, get_revision_detail, \
    rollback_to_revision, save_article_revision
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/articles", tags=["article-revisions"])


@router.post("/{article_id}/revisions")
async def create_article_revision(
        article_id: int,
        change_summary: str = Query(None, description="变更说明"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    手动创建文章修订版本
    
    Args:
        article_id: 文章ID
        change_summary: 变更说明（可选）
    """
    try:
        revision = await save_article_revision(
            db=db,
            article_id=article_id,
            author_id=current_user.id,
            change_summary=change_summary
        )

        if not revision:
            return ApiResponse(
                success=False,
                error="创建修订失败，文章可能不存在"
            )

        return ApiResponse(
            success=True,
            data={
                "message": "修订版本已保存",
                "revision": revision.to_dict()
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/{article_id}/revisions")
async def list_article_revisions(
        article_id: int,
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(20, ge=1, le=100, description="每页数量"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取文章的修订历史列表
    
    Args:
        article_id: 文章ID
        page: 页码
        per_page: 每页数量
    """
    try:
        result = await get_article_revisions(
            db=db,
            article_id=article_id,
            page=page,
            per_page=per_page
        )

        return ApiResponse(
            success=True,
            data=result
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/revisions/{revision_id}")
async def get_revision(
        revision_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取特定修订版本的详细信息
    
    Args:
        revision_id: 修订ID
    """
    try:
        revision = await get_revision_detail(
            db=db,
            revision_id=revision_id
        )

        if not revision:
            return ApiResponse(
                success=False,
                error="修订版本不存在"
            )

        return ApiResponse(
            success=True,
            data=revision
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/{article_id}/revisions/{revision_id}/rollback")
async def rollback_article(
        article_id: int,
        revision_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    回滚文章到指定修订版本
    
    Args:
        article_id: 文章ID
        revision_id: 目标修订ID
    """
    try:
        success = await rollback_to_revision(
            db=db,
            article_id=article_id,
            revision_id=revision_id,
            author_id=current_user.id
        )

        if not success:
            return ApiResponse(
                success=False,
                error="回滚失败，请检查文章和修订版本是否存在"
            )

        return ApiResponse(
            success=True,
            data={"message": "文章已成功回滚到指定版本"}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/revisions/compare")
async def compare_article_revisions(
        revision1_id: int = Query(..., description="第一个修订ID"),
        revision2_id: int = Query(..., description="第二个修订ID"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    比较两个修订版本的差异
    
    Args:
        revision1_id: 第一个修订ID
        revision2_id: 第二个修订ID
    """
    try:
        result = await compare_revisions(
            db=db,
            revision1_id=revision1_id,
            revision2_id=revision2_id
        )

        if not result:
            return ApiResponse(
                success=False,
                error="无法比较，修订版本可能不存在"
            )

        return ApiResponse(
            success=True,
            data=result
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))
