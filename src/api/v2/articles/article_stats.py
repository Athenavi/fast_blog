"""
文章阅读统计 API - V2 优化版
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.articles.article_view_stats import article_view_stats
from src.api.v2._helpers import ok
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
            return ok(msg=str(e))
    return wrapper


def _require_admin(user) -> bool:
    if not (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False)):
        raise HTTPException(403, "Admin access required.")
    return True


router = APIRouter(tags=["article-stats"])


@router.get("/{article_id}")
@_catch
async def get_article_views(article_id: int, current_user=Depends(jwt_required)):
    """获取文章阅读量"""
    count = await article_view_stats.get_view_count(article_id)
    return ok(data={"article_id": article_id, "views": count})


@router.post("/sync/{article_id}")
@_catch
async def sync_article_views(article_id: int, current_user=Depends(jwt_required),
                              db: AsyncSession = Depends(get_async_db)):
    """同步单篇文章阅读量到数据库（管理员）"""
    _require_admin(current_user)
    await article_view_stats.sync_to_database(article_id, db)
    return ok(msg=f"Article {article_id} views synced")


@router.post("/sync-all")
@_catch
async def sync_all_article_views(current_user=Depends(jwt_required),
                                  db: AsyncSession = Depends(get_async_db)):
    """批量同步所有文章阅读量（管理员）"""
    _require_admin(current_user)
    result = await article_view_stats.batch_sync_all(db)
    return ok(data=result, msg=f"Synced {result['synced']} articles")


@router.get("/top-articles")
@_catch
async def get_top_articles(limit: int = 10, current_user=Depends(jwt_required)):
    """获取热门文章排行"""
    top = await article_view_stats.get_top_articles(limit)
    return ok(data=[{"article_id": aid, "views": c} for aid, c in top])


@router.delete("/reset/{article_id}")
@_catch
async def reset_article_views(article_id: int, current_user=Depends(jwt_required)):
    """重置文章阅读计数（管理员）"""
    _require_admin(current_user)
    await article_view_stats.reset_article_views(article_id)
    return ok(msg=f"Article {article_id} view count reset")
