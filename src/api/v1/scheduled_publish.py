"""
文章定时发布API端点
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.scheduled_publish_service import (
    check_and_publish_scheduled_articles,
    get_scheduled_articles,
    cancel_scheduled_publish
)
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/articles", tags=["scheduled-publish"])


@router.post("/scheduled/check-and-publish")
async def trigger_scheduled_publish(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    手动触发检查并发布到期的定时文章
    
    注意：此接口通常需要管理员权限，实际使用时应添加权限检查
    """
    try:
        # 添加管理员权限检查
        from shared.services.permission_system import permission_manager
        is_admin = await permission_manager.has_permission(db, current_user.id, 'manage_articles')
        
        if not is_admin:
            return ApiResponse(success=False, error="权限不足，需要管理员权限")

        result = await check_and_publish_scheduled_articles(db=db)

        if not result["success"]:
            return ApiResponse(
                success=False,
                error=result.get("error", "检查定时发布失败")
            )

        return ApiResponse(
            success=True,
            data={
                "message": f"成功发布 {result['published_count']} 篇文章",
                "published_count": result["published_count"],
                "failed_count": result["failed_count"],
                "total_checked": result["total_checked"],
                "published_articles": result["published_articles"]
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/scheduled/list")
async def list_scheduled_articles(
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(20, ge=1, le=100, description="每页数量"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取待发布的定时文章列表
    
    Args:
        page: 页码
        per_page: 每页数量
    """
    try:
        result = await get_scheduled_articles(
            db=db,
            page=page,
            per_page=per_page
        )

        if not result["success"]:
            return ApiResponse(
                success=False,
                error=result.get("error", "获取定时文章列表失败")
            )

        return ApiResponse(
            success=True,
            data=result
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/{article_id}/scheduled/cancel")
async def cancel_article_schedule(
        article_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    取消文章的定时发布
    
    Args:
        article_id: 文章ID
    """
    try:
        success = await cancel_scheduled_publish(
            db=db,
            article_id=article_id
        )

        if not success:
            return ApiResponse(
                success=False,
                error="取消定时发布失败，文章可能不存在"
            )

        return ApiResponse(
            success=True,
            data={"message": "已取消定时发布"}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))
