"""
个性化推荐 API
提供文章推荐、Trending、Rising Stars等功能
"""
from functools import wraps
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query

from shared.services.advanced_features.recommendation_service import recommendation_service
from src.api.v2._helpers import ok, fail, _catch

router = APIRouter(tags=["recommendations"])


@router.get("/personalized", summary="获取个性化推荐")
@_catch
async def get_personalized_recommendations(
        limit: int = Query(10, ge=1, le=50, description="返回数量"),
        user_id: Optional[int] = Query(None, description="用户ID(可选)"),
):
    """获取个性化推荐文章"""
    if user_id:
        recommendations = recommendation_service.get_personalized_recommendations(user_id=user_id, limit=limit)
    else:
        recommendations = recommendation_service._get_popular_articles(limit)
    return ok(data={
        'recommendations': recommendations, 'count': len(recommendations),
        'algorithm': 'collaborative_filtering' if user_id else 'popularity_based',
    })


@router.get("/trending", summary="获取Trending文章")
@_catch
async def get_trending_articles(
        window: str = Query('24h', enum=['24h', '7d', '30d'], description="时间窗口"),
        limit: int = Query(10, ge=1, le=50, description="返回数量"),
):
    """获取Trending热门文章"""
    trending = recommendation_service.get_trending_articles(window=window, limit=limit)
    return ok(data={'trending': trending, 'count': len(trending), 'window': window})


@router.get("/rising-stars", summary="获取Rising Stars新锐博主")
@_catch
async def get_rising_stars(limit: int = Query(10, ge=1, le=20, description="返回数量")):
    """获取Rising Stars(新锐博主)"""
    rising_stars = recommendation_service.get_rising_stars(limit=limit)
    return ok(data={'rising_stars': rising_stars, 'count': len(rising_stars)})


@router.get("/similar/{article_id}", summary="获取相似文章")
@_catch
async def get_similar_articles(
        article_id: int,
        limit: int = Query(5, ge=1, le=20, description="返回数量"),
):
    """获取与指定文章相似的文章"""
    similar = recommendation_service.get_similar_articles(article_id=article_id, limit=limit)
    return ok(data={'similar_articles': similar, 'count': len(similar), 'reference_article_id': article_id})


@router.post("/track-action", summary="记录用户行为")
@_catch
async def track_user_action(
        user_id: int = Query(..., description="用户ID"),
        article_id: int = Query(..., description="文章ID"),
        action_type: str = Query('view', enum=['view', 'like', 'bookmark', 'comment'], description="行为类型"),
):
    """记录用户行为用于推荐算法"""
    recommendation_service.record_user_action(user_id=user_id, article_id=article_id, action_type=action_type)
    return ok(data={'user_id': user_id, 'article_id': article_id, 'action_type': action_type},
              message=f'Recorded {action_type} action')


@router.post("/update-article-features", summary="更新文章特征")
@_catch
async def update_article_features(
        article_id: int = Query(..., description="文章ID"),
        tags: List[str] = Query([], description="标签列表"),
        category: str = Query('', description="分类"),
        views: int = Query(0, description="浏览量"),
        likes: int = Query(0, description="点赞数"),
        created_at: Optional[str] = Query(None, description="创建时间"),
):
    """更新文章特征数据"""
    features = {'tags': tags, 'category': category, 'views': views, 'likes': likes, 'created_at': created_at}
    recommendation_service.update_article_features(article_id, features)
    return ok(data={'article_id': article_id}, message='Article features updated')
