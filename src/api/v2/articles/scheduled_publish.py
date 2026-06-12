"""
文章定时发布 API - V2 优化版
"""
from datetime import datetime
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.articles.scheduled_publish import create_scheduled_publish_service
from src.utils.database.main import get_async_session


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (ValueError, HTTPException):
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return wrapper


router = APIRouter(tags=["scheduled-publish"])


class ScheduleArticleRequest(BaseModel):
    article_id: int
    publish_at: str


@router.post("/schedule")
@_catch
async def schedule_article(request: ScheduleArticleRequest, db: AsyncSession = Depends(get_async_session)):
    """设置定时发布"""
    publish_at = datetime.fromisoformat(request.publish_at)
    service = create_scheduled_publish_service(db)
    result = await service.schedule_article(article_id=request.article_id, publish_at=publish_at)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.post("/cancel/{article_id}")
@_catch
async def cancel_scheduled_publish(article_id: int, db: AsyncSession = Depends(get_async_session)):
    """取消定时发布"""
    service = create_scheduled_publish_service(db)
    result = await service.cancel_scheduled_publish(article_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.post("/publish-due")
@_catch
async def publish_due_articles(db: AsyncSession = Depends(get_async_session)):
    """发布所有到期的定时文章"""
    service = create_scheduled_publish_service(db)
    return await service.publish_due_articles()


@router.get("/list")
@_catch
async def get_scheduled_articles(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200),
                                  db: AsyncSession = Depends(get_async_session)):
    """获取待发布文章列表"""
    service = create_scheduled_publish_service(db)
    limit = per_page
    offset = (page - 1) * per_page
    articles = await service.get_scheduled_articles(limit, offset)
    return {'success': True, 'data': articles, 'count': len(articles)}


@router.get("/upcoming")
@_catch
async def get_upcoming_publishes(hours: int = Query(24, ge=1, le=168),
                                  db: AsyncSession = Depends(get_async_session)):
    """获取即将发布的文章"""
    service = create_scheduled_publish_service(db)
    articles = await service.get_upcoming_publishes(hours)
    return {'success': True, 'data': articles, 'count': len(articles), 'hours': hours}
