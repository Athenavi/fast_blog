"""
个性化动态流 API
提供基于关注的个性化内容推荐和动态流
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.models.user import User as UserModel
from shared.services.advanced_features.personalized_feed_service import personalized_feed_service
from src.api.v2._helpers import ok, fail, _catch
from src.auth.auth_deps import get_current_active_user

router = APIRouter(tags=["feed"])


@router.get("/my-feed", summary="获取我的动态流")
@_catch
async def get_my_feed(
        limit: int = Query(50, ge=1, le=200, description="返回数量"),
        offset: int = Query(0, ge=0, description="偏移量"),
        event_type: str = Query(None, enum=['article_published', 'commented', 'liked', 'followed'],
                                description="事件类型过滤"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """获取当前用户的个性化动态流"""
    feed = personalized_feed_service.get_user_feed(
        user_id=current_user.id, limit=limit, offset=offset, event_type=event_type,
    )
    return ok(data={'feed': feed, 'count': len(feed), 'has_more': len(feed) == limit})


@router.post("/simulate/article-published", summary="模拟文章发布事件")
@_catch
async def simulate_article_published(
        article_id: int = Body(..., embed=True, description="文章ID"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """模拟文章发布事件(用于测试)"""
    event_id = personalized_feed_service.create_event(
        event_type='article_published', actor_id=current_user.id,
        target_id=article_id, content={'article_id': article_id, 'title': f'Article {article_id}'},
    )
    return ok(data={'event_id': event_id}, message='事件已创建')
