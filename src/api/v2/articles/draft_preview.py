"""
草稿预览链接 API - V2 优化版
"""
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article
from shared.models.article_content import ArticleContent
from shared.services.articles.draft_preview_service import draft_preview_service
from src.api.v2._base import ApiResponse
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return fail(str(e))
    return wrapper


router = APIRouter(tags=["draft-preview"])


class CreatePreviewRequest(BaseModel):
    article_id: int
    expires_hours: int = 24
    password: Optional[str] = None
    max_views: Optional[int] = None


@router.post("/generate")
@_catch
async def generate_preview_link(request: CreatePreviewRequest, current_user=Depends(jwt_required),
                                db: AsyncSession = Depends(get_async_db)):
    """生成草稿预览链接"""
    article = await db.scalar(select(Article).where(Article.id == request.article_id, Article.user_id == current_user.id))
    if not article:
        return fail("文章不存在或无权访问")

    token = draft_preview_service.generate_preview_token(
        article_id=request.article_id, expires_hours=request.expires_hours,
        password=request.password, max_views=request.max_views)
    preview_url = draft_preview_service.get_preview_url(token)

    return ok({'token': token, 'preview_url': preview_url, 'expires_hours': request.expires_hours,
               'has_password': request.password is not None, 'max_views': request.max_views})


@router.post("/validate")
@_catch
async def validate_preview_link(token: str = Body(...), password: Optional[str] = Body(None)):
    """验证预览链接并获取文章内容"""
    token_info = draft_preview_service.validate_preview_token(token=token, password=password)
    if not token_info:
        return fail("预览链接无效、已过期或密码错误")

    async with get_async_db() as db:
        row = (await db.execute(
            select(Article, ArticleContent)
            .outerjoin(ArticleContent, Article.id == ArticleContent.article_id)
            .where(Article.id == token_info['article_id'])
        )).first()

    if not row:
        return fail("文章不存在")
    article, content_obj = row

    return ok(data={'article': {
        'id': article.id, 'title': article.title, 'excerpt': article.excerpt,
        'cover_image': article.cover_image,
        'created_at': article.created_at.isoformat() if article.created_at else None,
        'updated_at': article.updated_at.isoformat() if article.updated_at else None,
    }, 'content': content_obj.content if content_obj else '',
        'view_count': token_info.get('view_count', 0)})


@router.post("/revoke")
@_catch
async def revoke_preview_link(token: str = Body(..., embed=True), current_user=Depends(jwt_required)):
    """撤销预览链接"""
    if not draft_preview_service.revoke_token(token):
        return fail("预览链接不存在")
    return ok(msg="预览链接已撤销")


@router.get("/stats/{token}")
@_catch
async def get_preview_stats(token: str, current_user=Depends(jwt_required)):
    """预览链接统计"""
    stats = draft_preview_service.get_token_stats(token)
    if not stats:
        return fail("预览链接不存在")
    return ok(data=stats)


@router.post("/cleanup")
@_catch
async def cleanup_expired_tokens(current_user=Depends(jwt_required)):
    """清理过期预览令牌（管理员）"""
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        return fail("Admin access required.")
    count = draft_preview_service.cleanup_expired_tokens()
    return ok(data={'cleaned_count': count}, msg=f"清理了 {count} 个过期令牌")
