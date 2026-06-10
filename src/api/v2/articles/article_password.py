"""
文章密码保护 API - V2 优化版
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article
from src.api.v2._base import ApiResponse
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db


router = APIRouter(tags=["article-password"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return fail(str(e))
    return wrapper


@router.get("/access/{article_id}")
@_catch
async def check_article_access(article_id: int, password: str = Query(""),
                                db: AsyncSession = Depends(get_async_db)):
    """验证文章密码"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        return fail("文章不存在")
    if not article.password:
        return ok({"has_password": False})
    if password == article.password:
        return ok({"has_password": True, "access_granted": True})
    return ok({"has_password": True, "access_granted": False})


@router.post("/verify/{article_id}")
@_catch
async def verify_article_password(article_id: int, data: dict,
                                   db: AsyncSession = Depends(get_async_db)):
    """验证文章访问密码"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        return fail("文章不存在")
    if not article.password:
        return ok({"verified": True})
    if data.get('password') == article.password:
        return ok({"verified": True})
    return ok({"verified": False})


@router.post("/set/{article_id}")
@_catch
async def set_article_password(article_id: int, data: dict,
                                db: AsyncSession = Depends(get_async_db),
                                current_user=Depends(jwt_required)):
    """设置/更改文章密码"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        return fail("文章不存在")
    if article.user_id != current_user.id and not getattr(current_user, 'is_superuser', False):
        return fail("无权限修改此文章密码")
    article.password = data.get('password', '')
    await db.commit()
    return ok(msg="密码更新成功")


@router.delete("/remove/{article_id}")
@_catch
async def remove_article_password(article_id: int,
                                   db: AsyncSession = Depends(get_async_db),
                                   current_user=Depends(jwt_required)):
    """移除文章密码"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        return fail("文章不存在")
    if article.user_id != current_user.id and not getattr(current_user, 'is_superuser', False):
        return fail("无权限移除密码")
    article.password = None
    article.password_hint = None
    await db.commit()
    return ok(msg="密码已移除")
