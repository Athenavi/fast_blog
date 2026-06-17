"""
文章修订历史 API - V2 优化版
"""
from datetime import datetime, timezone
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article, ArticleContent
from shared.models.user import User
from shared.services.articles.article_manager import compare_revisions, get_article_revisions, \
    get_revision_detail, rollback_to_revision, save_article_revision, delete_revision
from src.api.v2._base import ApiResponse
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
            return fail(str(e))
    return wrapper


def _is_admin(user) -> bool:
    return user and (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))


async def _check_article_access(article_id: int, current_user: User, db: AsyncSession) -> Article:
    """检查文章存在且当前用户有权访问"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    if article.user != current_user.id and not _is_admin(current_user):
        raise HTTPException(403, "无权操作此文章")
    return article


router = APIRouter(tags=["article-revisions"])


class CreateRevisionRequest(BaseModel):
    change_summary: Optional[str] = None
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    cover_image: Optional[str] = None
    tags: Optional[str] = None
    category_id: Optional[int] = None


@router.post("/{article_id}/revisions")
@_catch
async def create_article_revision(article_id: int, req: CreateRevisionRequest = Body(None),
                                   current_user=Depends(jwt_required),
                                   db: AsyncSession = Depends(get_async_db)):
    """创建修订版本或同步本地草稿"""
    await _check_article_access(article_id, current_user, db)
    if req and (req.title or req.content):
        row = (await db.execute(
            select(Article, ArticleContent)
            .outerjoin(ArticleContent, Article.id == ArticleContent.article)
            .where(Article.id == article_id)
        )).first()
        if not row:
            return fail("文章不存在")
        article, content_obj = row
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if req.title is not None: article.title = req.title
        if req.excerpt is not None: article.excerpt = req.excerpt
        if req.cover_image is not None: article.cover_image = req.cover_image
        if req.tags is not None: article.tags_list = req.tags
        if req.category_id is not None: article.category = req.category_id
        if req.content is not None:
            if content_obj:
                content_obj.content = req.content
                content_obj.updated_at = now
            else:
                db.add(ArticleContent(article=article_id, content=req.content, created_at=now, updated_at=now))
        article.updated_at = now
        await db.commit()

    revision = await save_article_revision(db=db, article_id=article_id, author_id=current_user.id,
                                           change_summary=req.change_summary if req else None)
    if not revision:
        return ok(data={"message": "内容未发生变化，已跳过", "skipped": True, "reason": "deduplication"})
    return ok(data={"message": "修订版本已保存", "revision": revision.to_dict()})


@router.get("/{article_id}/revisions")
@_catch
async def list_article_revisions(article_id: int, page: int = Query(1, ge=1),
                                  per_page: int = Query(20, ge=1, le=100),
                                  current_user=Depends(jwt_required),
                                  db: AsyncSession = Depends(get_async_db)):
    """获取文章的修订历史列表"""
    await _check_article_access(article_id, current_user, db)
    result = await get_article_revisions(db=db, article_id=article_id, page=page, per_page=per_page)
    return ok(data=result)


@router.get("/revisions/compare")
@_catch
async def compare_article_revisions(revision1_id: int = Query(...), revision2_id: int = Query(...),
                                     current_user=Depends(jwt_required),
                                     db: AsyncSession = Depends(get_async_db)):
    """比较两个修订版本的差异（需要访问对应文章权限）"""
    from shared.models.article import ArticleRevision as RevModel

    # 加载两个修订版本
    revs_query = select(RevModel).where(RevModel.id.in_([revision1_id, revision2_id]))
    revs_result = await db.execute(revs_query)
    revisions = revs_result.scalars().all()

    if len(revisions) != 2:
        return fail("修订版本不存在")

    rev1, rev2 = revisions[0], revisions[1]

    # 验证它们属于同一篇文章
    if rev1.article_id != rev2.article_id:
        return fail("两个修订版本不属于同一篇文章，无法比较")

    # 验证当前用户对该文章有访问权限
    await _check_article_access(rev1.article_id, current_user, db)

    result = await compare_revisions(db=db, revision1_id=revision1_id, revision2_id=revision2_id)
    if not result:
        return fail("无法比较，修订版本可能不存在")
    return ok(data=result)


@router.get("/{article_id}/revisions/{revision_id}")
@_catch
async def get_revision(article_id: int, revision_id: int, current_user=Depends(jwt_required),
                        db: AsyncSession = Depends(get_async_db)):
    """获取特定修订版本的详细信息"""
    await _check_article_access(article_id, current_user, db)
    revision = await get_revision_detail(db=db, revision_id=revision_id)
    if not revision:
        return fail("修订版本不存在")
    return ok(data=revision)


@router.post("/{article_id}/revisions/{revision_id}/rollback")
@_catch
async def rollback_article(article_id: int, revision_id: int,
                            current_user=Depends(jwt_required),
                            db: AsyncSession = Depends(get_async_db)):
    """回滚文章到指定修订版本"""
    await _check_article_access(article_id, current_user, db)
    success = await rollback_to_revision(db=db, article_id=article_id, revision_id=revision_id, author_id=current_user.id)
    if not success:
        return fail("回滚失败，请检查文章和修订版本是否存在")
    return ok(msg="文章已成功回滚到指定版本")


@router.post("/{article_id}/revisions/sync")
@_catch
async def sync_article_revisions(article_id: int, current_user=Depends(jwt_required),
                                  db: AsyncSession = Depends(get_async_db)):
    """同步文章修订历史到云端"""
    await _check_article_access(article_id, current_user, db)
    revision = await save_article_revision(db=db, article_id=article_id, author_id=current_user.id, change_summary="手动同步到云端")
    if not revision:
        return fail("同步失败，文章可能不存在")
    return ok(data={"revision": revision.to_dict()}, msg="修订历史已同步到云端")


@router.delete("/{article_id}/revisions/{revision_id}")
@_catch
async def delete_article_revision(article_id: int, revision_id: int,
                                   current_user=Depends(jwt_required),
                                   db: AsyncSession = Depends(get_async_db)):
    """删除指定修订版本"""
    await _check_article_access(article_id, current_user, db)
    success = await delete_revision(db=db, revision_id=revision_id, article_id=article_id)
    if not success:
        return fail("删除失败，修订版本可能不存在")
    return ok(msg="修订版本已成功删除")
