"""
个性化动态流 API
提供基于关注的个性化内容推荐和动态流
"""

from fastapi import APIRouter, Depends, Query, Body

from shared.models.user import User as UserModel
from shared.services.advanced_features.personalized_feed_service import personalized_feed_service
from src.api.v1.core.responses import ApiResponse
from src.auth.auth_deps import get_current_active_user

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("/my-feed", summary="获取我的动态流")
async def get_my_feed(
        limit: int = Query(50, ge=1, le=200, description="返回数量"),
        offset: int = Query(0, ge=0, description="偏移量"),
        event_type: str = Query(None, enum=['article_published', 'commented', 'liked', 'followed'],
                                description="事件类型过滤"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    获取当前用户的个性化动态流
    
    Args:
        limit: 返回数量(1-200)
        offset: 偏移量
        event_type: 事件类型过滤
        
    Returns:
        动态流列表
    """
    try:
        feed = personalized_feed_service.get_user_feed(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            event_type=event_type,
        )

        return ApiResponse(
            success=True,
            data={
                'feed': feed,
                'count': len(feed),
                'has_more': len(feed) == limit,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取动态流失败: {str(e)}")


@router.post("/follow", summary="关注用户")
async def follow_user(
        user_id: int = Body(..., embed=True, description="目标用户ID"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    关注指定用户
    
    Args:
        user_id: 目标用户ID
        
    Returns:
        操作结果
    """
    try:
        if user_id == current_user.id:
            return ApiResponse(success=False, error='不能关注自己')

        success = personalized_feed_service.follow_user(current_user.id, user_id)

        if success:
            # 创建关注事件
            personalized_feed_service.create_event(
                event_type='followed',
                actor_id=current_user.id,
                target_id=user_id,
            )

            return ApiResponse(
                success=True,
                message='关注成功'
            )
        else:
            return ApiResponse(success=False, error='关注失败')
    except Exception as e:
        return ApiResponse(success=False, error=f"关注失败: {str(e)}")


@router.post("/unfollow", summary="取消关注")
async def unfollow_user(
        user_id: int = Body(..., embed=True, description="目标用户ID"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    取消关注指定用户
    
    Args:
        user_id: 目标用户ID
        
    Returns:
        操作结果
    """
    try:
        success = personalized_feed_service.unfollow_user(current_user.id, user_id)

        if success:
            return ApiResponse(
                success=True,
                message='已取消关注'
            )
        else:
            return ApiResponse(success=False, error='取消关注失败')
    except Exception as e:
        return ApiResponse(success=False, error=f"操作失败: {str(e)}")


@router.get("/following-list", summary="获取我的关注列表")
async def get_following_list(
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    获取当前用户的关注列表
    
    Returns:
        关注用户ID列表
    """
    try:
        followings = personalized_feed_service.get_followings(current_user.id)

        return ApiResponse(
            success=True,
            data={
                'followings': followings,
                'count': len(followings),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取列表失败: {str(e)}")


@router.get("/follower-list", summary="获取我的粉丝列表")
async def get_follower_list(
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    获取当前用户的粉丝列表
    
    Returns:
        粉丝用户ID列表
    """
    try:
        followers = personalized_feed_service.get_followers(current_user.id)

        return ApiResponse(
            success=True,
            data={
                'followers': followers,
                'count': len(followers),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取列表失败: {str(e)}")


@router.get("/check-follow/{user_id}", summary="检查是否关注")
async def check_follow(
        user_id: int,
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    检查是否关注指定用户
    
    Args:
        user_id: 目标用户ID
        
    Returns:
        关注状态
    """
    try:
        is_following = personalized_feed_service.is_following(current_user.id, user_id)

        return ApiResponse(
            success=True,
            data={
                'is_following': is_following,
                'target_user_id': user_id,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"检查失败: {str(e)}")


@router.get("/mutual-followings/{user_id}", summary="获取共同关注")
async def get_mutual_followings(
        user_id: int,
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    获取与指定用户的共同关注
    
    Args:
        user_id: 目标用户ID
        
    Returns:
        共同关注的用户ID列表
    """
    try:
        mutual = personalized_feed_service.get_mutual_followings(current_user.id, user_id)

        return ApiResponse(
            success=True,
            data={
                'mutual_followings': mutual,
                'count': len(mutual),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取失败: {str(e)}")


@router.get("/stats", summary="获取动态流统计")
async def get_feed_stats(
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    获取当前用户的动态流统计
    
    Returns:
        统计数据
    """
    try:
        stats = personalized_feed_service.get_feed_stats(current_user.id)

        return ApiResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取统计失败: {str(e)}")


# 模拟事件创建接口(实际应该在其他业务逻辑中调用)

@router.post("/simulate/article-published", summary="模拟文章发布事件")
async def simulate_article_published(
        article_id: int = Body(..., embed=True, description="文章ID"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    模拟文章发布事件(用于测试)
    
    Args:
        article_id: 文章ID
        
    Returns:
        操作结果
    """
    try:
        event_id = personalized_feed_service.create_event(
            event_type='article_published',
            actor_id=current_user.id,
            target_id=article_id,
            content={
                'article_id': article_id,
                'title': f'Article {article_id}',
            },
        )

        return ApiResponse(
            success=True,
            message='事件已创建',
            data={
                'event_id': event_id,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"创建失败: {str(e)}")
