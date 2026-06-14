"""
评论增强 API
"""

from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.comments.comment_enhanced import comment_enhanced_service
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["comments-enhanced"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            return fail(str(e))
    return wrapper


@router.get("/article/{article_id}")
@_catch
async def get_article_comments(
        article_id: int,
        sort_by: str = Query(default='latest', enum=['latest', 'oldest', 'popular']),
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1, le=100),
        db: AsyncSession = Depends(get_async_db),
):
    """
    获取文章的评论树
    
    Args:
        article_id: 文章ID
        sort_by: 排序方式 (latest, oldest, popular)
        page: 页码
        per_page: 每页数量
        
    Returns:
        评论树和分页信息
    """
    result = await comment_enhanced_service.get_comments_tree(
        db=db,
        article_id=article_id,
        sort_by=sort_by,
        page=page,
        per_page=per_page
    )

    return {
        "success": True,
        "data": result
    }


@router.post("/{comment_id}/like")
@_catch
async def like_comment(
        comment_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db),
):
    """
    点赞评论
    
    Args:
        comment_id: 评论ID
        
    Returns:
        操作结果
    """
    result = await comment_enhanced_service.like_comment(
        db=db,
        comment_id=comment_id,
        user_id=current_user.id
    )

    return {
        "success": True,
        "data": result
    }


@router.post("/{comment_id}/dislike")
@_catch
async def dislike_comment(
        comment_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db),
):
    """
    反对评论
    
    Args:
        comment_id: 评论ID
        
    Returns:
        操作结果
    """
    result = await comment_enhanced_service.dislike_comment(
        db=db,
        comment_id=comment_id,
        user_id=current_user.id
    )

    return {
        "success": True,
        "data": result
    }


@router.get("/{comment_id}/vote")
@_catch
async def get_user_vote(
        comment_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db),
):
    """
    获取用户对评论的投票
    
    Args:
        comment_id: 评论ID
        
    Returns:
        投票类型 (like, dislike, null)
    """
    vote_type = await comment_enhanced_service.get_user_vote(
        db=db,
        comment_id=comment_id,
        user_id=current_user.id
    )

    return {
        "success": True,
        "data": {
            "vote_type": vote_type
        }
    }


@router.post("/{comment_id}/notify-reply")
@_catch
async def notify_comment_reply(
        comment_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db),
):
    """
    通知评论被回复（通常在创建回复评论后调用）
    
    Args:
        comment_id: 新评论ID
        
    Returns:
        通知结果
    """
    result = await comment_enhanced_service.notify_comment_reply(
        db=db,
        comment_id=comment_id
    )

    return {
        "success": result['success'],
        "data": result
    }
