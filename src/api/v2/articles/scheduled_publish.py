"""
文章定时发布 API - V2 优化版
"""
from datetime import datetime
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article
from shared.services.articles.scheduled_publish import create_scheduled_publish_service
from src.api.v2._helpers import ok, fail
from src.utils.database.main import get_async_session
from src.auth import jwt_required_dependency as jwt_required


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            return fail(str(e))

    return wrapper


router = APIRouter(tags=["scheduled-publish"])


class ScheduleArticleRequest(BaseModel):
    article_id: int
    publish_at: str


@router.get("/list")
@_catch
async def get_scheduled_articles(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200),
                                  current_user=Depends(jwt_required),
                                  db: AsyncSession = Depends(get_async_session)):
    """获取待发布文章列表"""
    service = create_scheduled_publish_service(db)
    limit = per_page
    offset = (page - 1) * per_page
    # 管理员可查看全部，普通用户只能查看自己的
    user_id = None if getattr(current_user, 'is_superuser', False) else current_user.id
    articles = await service.get_scheduled_articles(limit, offset, user_id=user_id)
    return ok(data={'items': articles, 'count': len(articles)})


@router.get("/upcoming")
@_catch
async def get_upcoming_publishes(hours: int = Query(24, ge=1, le=168),
                                  current_user=Depends(jwt_required),
                                  db: AsyncSession = Depends(get_async_session)):
    """获取即将发布的文章"""
    service = create_scheduled_publish_service(db)
    # 管理员可查看全部，普通用户只能查看自己的
    user_id = None if getattr(current_user, 'is_superuser', False) else current_user.id
    articles = await service.get_upcoming_publishes(hours, user_id=user_id)
    return ok(data={'items': articles, 'count': len(articles), 'hours': hours})


@router.post("/schedule")
@_catch
async def schedule_article(request: ScheduleArticleRequest,
                            current_user=Depends(jwt_required),
                            db: AsyncSession = Depends(get_async_session)):
    """设置定时发布"""
    # 验证文章归属
    article = await db.scalar(select(Article).where(Article.id == request.article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    if article.user != current_user.id and not getattr(current_user, 'is_superuser', False):
        raise HTTPException(403, "无权操作此文章")

    publish_at = datetime.fromisoformat(request.publish_at)
    service = create_scheduled_publish_service(db)
    result = await service.schedule_article(article_id=request.article_id, publish_at=publish_at)
    if not result['success']:
        return fail(result['message'])
    return ok(msg="定时发布已设置", data={'article_id': request.article_id, 'publish_at': request.publish_at})


@router.post("/cancel/{article_id}")
@_catch
async def cancel_scheduled_publish(article_id: int,
                                    current_user=Depends(jwt_required),
                                    db: AsyncSession = Depends(get_async_session)):
    """取消定时发布"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    if article.user != current_user.id and not getattr(current_user, 'is_superuser', False):
        raise HTTPException(403, "无权操作此文章")

    service = create_scheduled_publish_service(db)
    result = await service.cancel_scheduled_publish(article_id)
    if not result['success']:
        return fail(result['message'])
    return ok(msg="定时发布已取消", data={'article_id': article_id})


@router.post("/publish-due")
@_catch
async def publish_due_articles(current_user=Depends(jwt_required),
                                db: AsyncSession = Depends(get_async_session)):
    """发布所有到期的定时文章"""
    service = create_scheduled_publish_service(db)
    return await service.publish_due_articles()
