"""
文章阅读统计 API
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.articles.article_view_stats import article_view_stats
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["article-stats"])


@router.post("/view/{article_id}")
async def record_article_view(
        article_id: int,
        request: Request,
        current_user=Depends(jwt_required),
):
    """
    记录文章阅读
    
    Args:
        article_id: 文章ID
        
    Returns:
        记录结果
    """
    # 获取用户信息（如果已登录）
    user_id = current_user.id if current_user else None

    # 获取 IP
    ip = request.client.host if request.client else None

    # 记录阅读
    recorded = await article_view_stats.record_view(
        article_id=article_id,
        user_id=user_id,
        ip=ip
    )

    return {
        "success": True,
        "recorded": recorded,
        "message": "View recorded" if recorded else "View skipped (anti-spam)"
    }


@router.get("/view/{article_id}")
async def get_article_views(
        article_id: int,
        current_user=Depends(jwt_required),
):
    """
    获取文章阅读量
    
    Args:
        article_id: 文章ID
        
    Returns:
        阅读量
    """
    view_count = await article_view_stats.get_view_count(article_id)

    return {
        "success": True,
        "data": {
            "article_id": article_id,
            "views": view_count
        }
    }


@router.post("/sync/{article_id}")
async def sync_article_views(
        article_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db),
):
    """
    同步单篇文章阅读量到数据库（管理员）
    
    Args:
        article_id: 文章ID
        
    Returns:
        同步结果
    """
    # TODO: 添加管理员权限检查

    await article_view_stats.sync_to_database(article_id, db)

    return {
        "success": True,
        "message": f"Article {article_id} views synced to database"
    }


@router.post("/sync-all")
async def sync_all_article_views(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db),
):
    """
    批量同步所有文章阅读量到数据库（管理员）
    
    Returns:
        同步结果
    """
    # TODO: 添加管理员权限检查

    result = await article_view_stats.batch_sync_all(db)

    return {
        "success": True,
        "data": result,
        "message": f"Synced {result['synced']} articles"
    }


@router.get("/top-articles")
async def get_top_articles(
        limit: int = 10,
        current_user=Depends(jwt_required),
):
    """
    获取热门文章
    
    Args:
        limit: 返回数量
        
    Returns:
        热门文章列表
    """
    top_articles = await article_view_stats.get_top_articles(limit)

    return {
        "success": True,
        "data": [
            {"article_id": aid, "views": count}
            for aid, count in top_articles
        ]
    }


@router.delete("/reset/{article_id}")
async def reset_article_views(
        article_id: int,
        current_user=Depends(jwt_required),
):
    """
    重置文章阅读计数（管理员）
    
    Args:
        article_id: 文章ID
        
    Returns:
        操作结果
    """
    # TODO: 添加管理员权限检查

    await article_view_stats.reset_article_views(article_id)

    return {
        "success": True,
        "message": f"Article {article_id} view count reset"
    }
