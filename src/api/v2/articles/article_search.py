"""
文章搜索 API - V2 优化版
"""
from datetime import datetime
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.articles.article_search import article_search_service
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return wrapper


router = APIRouter(tags=["search"])


def _parse_date(s: str, name: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, f"Invalid {name} format. Use YYYY-MM-DD")


@router.get("")
@_catch
async def search_articles(
        q: str = Query(..., min_length=1),
        category_id: Optional[int] = Query(None),
        author_id: Optional[int] = Query(None),
        date_from: Optional[str] = Query(None),
        date_to: Optional[str] = Query(None),
        status: str = Query("published"),
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        sort_by: str = Query("relevance"),
        db: AsyncSession = Depends(get_async_db),
):
    result = await article_search_service.search_articles(
        db=db, query=q, category_id=category_id, author_id=author_id,
        date_from=_parse_date(date_from, "date_from"), date_to=_parse_date(date_to, "date_to"),
        status=status, page=page, per_page=per_page, sort_by=sort_by)
    return {"success": True, "data": result}


@router.get("/suggestions")
@_catch
async def get_search_suggestions(q: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=10),
                                  db: AsyncSession = Depends(get_async_db)):
    suggestions = await article_search_service.get_search_suggestions(db=db, query=q, limit=limit)
    return {"success": True, "data": {"query": q, "suggestions": suggestions}}


@router.get("/popular")
@_catch
async def get_popular_searches(days: int = Query(7, ge=1, le=30), limit: int = Query(10, ge=1, le=20),
                                db: AsyncSession = Depends(get_async_db)):
    popular = await article_search_service.get_popular_searches(db=db, days=days, limit=limit)
    return {"success": True, "data": popular}


@router.post("/history/clear")
@_catch
async def clear_search_history(days: int = Query(30, ge=1), current_user=Depends(jwt_required),
                                db: AsyncSession = Depends(get_async_db)):
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(403, detail="Admin access required.")
    await article_search_service.clear_old_search_history(db=db, days=days)
    return {"success": True, "message": f"已清理 {days} 天前的搜索历史"}
