"""
文章评分 API
提供评分提交、查询等功能
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Request

from shared.models import User
from shared.services.plugins.plugin_manager.core import plugin_manager
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required, jwt_optional_dependency

router = APIRouter(tags=["article-rating"])


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


@router.post("/rate")
@_catch
async def submit_article_rating(
        request: Request,
        current_user: User = Depends(jwt_required)
):
    """
    提交文章评分
    
    Body参数:
        article_id: 文章ID
        rating: 评分 (1-5)
        comment: 评论（可选）
    """
    body = await request.json()
    article_id = body.get('article_id')
    rating = body.get('rating')
    comment = body.get('comment', '')

    if not article_id or not rating:
        return fail('缺少必要参数')

    rating_plugin = plugin_manager.get_plugin('article-rating')
    if not rating_plugin:
        return fail('评分插件未加载')

    if not rating_plugin.active:
        return fail('评分功能未启用')

    rating_data = {
        'article_id': str(article_id),
        'user_id': str(current_user.id),
        'rating': rating,
        'comment': comment,
        'ip': request.client.host if request.client else '',
    }

    result = rating_plugin.handle_rating_submission(rating_data)

    return result


@router.get("/{article_id}/stats")
@_catch
async def get_article_rating_stats(
        article_id: str,
        current_user: User = Depends(jwt_optional_dependency)
):
    """
    获取文章评分统计
    """
    rating_plugin = plugin_manager.get_plugin('article-rating')
    if not rating_plugin:
        return fail('评分插件未加载')

    stats = rating_plugin.get_article_stats(article_id)

    user_rating = None
    if current_user:
        user_rating_obj = rating_plugin.get_user_rating(str(current_user.id), article_id)
        if user_rating_obj:
            user_rating = user_rating_obj['rating']

    return ok(data={
        'stats': stats,
        'user_rating': user_rating,
    })


@router.get("/{article_id}/ratings")
@_catch
async def get_article_ratings(
        article_id: str,
        limit: int = 10,
        current_user: User = Depends(jwt_optional_dependency)
):
    """
    获取文章的评分列表
    """
    rating_plugin = plugin_manager.get_plugin('article-rating')
    if not rating_plugin:
        return fail('评分插件未加载')

    ratings = rating_plugin.get_recent_ratings(article_id=article_id, limit=limit)

    return ok(data=ratings)
