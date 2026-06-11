"""
评论订阅API
"""
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.comments.comment_manager import comment_subscription_service
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required, jwt_optional_dependency
from src.extensions import get_async_db_session as get_async_db

router = APIRouter()


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            print(f"Error: {str(e)}")
            traceback.print_exc()
            return fail(str(e))
    return wrapper


@router.post("/subscribe",
             summary="订阅文章评论",
             description="订阅指定文章的评论通知，支持用户和访客",
             response_description="返回订阅结果")
@_catch
async def subscribe_to_article_api(
        article_id: int = Body(..., embed=True, description="文章ID"),
        email: str = Body(..., embed=True, description="订阅邮箱"),
        notify_type: str = Body('new_comment', embed=True, description="通知类型"),
        current_user=Depends(jwt_optional_dependency),
        db: AsyncSession = Depends(get_async_db)
):
    """订阅文章评论"""
    user_id = current_user.id if current_user else None
    
    result = await comment_subscription_service.subscribe_to_article(
        db=db,
        article_id=article_id,
        email=email,
        user_id=user_id,
        notify_type=notify_type
    )
    
    return ok(data=result)


@router.post("/unsubscribe",
             summary="取消订阅文章评论",
             description="取消对指定文章的评论订阅",
             response_description="返回操作结果")
@_catch
async def unsubscribe_from_article_api(
        article_id: int = Body(..., embed=True, description="文章ID"),
        email: str = Body(..., embed=True, description="订阅邮箱"),
        db: AsyncSession = Depends(get_async_db)
):
    """取消订阅文章评论"""
    result = await comment_subscription_service.unsubscribe_from_article(db, article_id, email)
    
    return ok(data=result)


@router.get("/confirm/{token}",
            summary="确认订阅",
            description="通过token确认订阅（访客）",
            response_description="返回确认结果")
@_catch
async def confirm_subscription_api(
        token: str,
        db: AsyncSession = Depends(get_async_db)
):
    """确认订阅"""
    result = await comment_subscription_service.confirm_subscription(db, token)
    
    return ok(data=result)


@router.get("/my-subscriptions",
            summary="获取我的订阅列表",
            description="获取当前用户的所有评论订阅",
            response_description="返回订阅列表")
@_catch
async def get_my_subscriptions_api(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取我的订阅列表"""
    subscriptions = await comment_subscription_service.get_user_subscriptions(db, current_user.id)
    
    return ok(
        data={
            "subscriptions": subscriptions,
            "total": len(subscriptions)
        }
    )


@router.get("/article/{article_id}/subscribers",
            summary="获取文章订阅者",
            description="获取指定文章的订阅者列表（用于发送通知）",
            response_description="返回订阅者列表")
@_catch
async def get_article_subscribers_api(
        article_id: int,
        notify_type: Optional[str] = Query(None, description="通知类型筛选"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取文章订阅者"""
    # 检查权限：仅管理员或文章作者可查看
    from sqlalchemy import select
    from shared.models.article import Article
    
    article_query = select(Article).where(Article.id == article_id)
    article_result = await db.execute(article_query)
    article = article_result.scalar_one_or_none()
    
    if not article:
        return fail("Article not found")
    
    if (not getattr(current_user, 'is_staff', False) and 
        not getattr(current_user, 'is_superuser', False) and
        article.user != current_user.id):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    subscribers = await comment_subscription_service.get_article_subscribers(db, article_id, notify_type)
    
    return ok(
        data={
            "subscribers": subscribers,
            "total": len(subscribers)
        }
    )
