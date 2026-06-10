"""
文章批注 API - V2 优化版
协作编辑时的评论和批注功能
"""
from datetime import datetime
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article, ArticleAnnotation
from shared.models.user import User
from src.api.v2._base import ApiResponse
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required
from src.utils.database.main import get_async_session


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return fail(f"{e}")
    return wrapper


def _fmt_ann(ann: ArticleAnnotation, users: dict[int, User]) -> dict:
    u = users.get(ann.user)
    return {
        'id': ann.id, 'article_id': ann.article, 'user_id': ann.user,
        'username': u.username if u else 'Unknown', 'content': ann.content,
        'position': ann.position, 'selection_text': ann.selection_text,
        'is_resolved': ann.is_resolved, 'parent_id': ann.parent,
        'created_at': ann.created_at.isoformat() if ann.created_at else None,
        'updated_at': ann.updated_at.isoformat() if ann.updated_at else None,
    }


router = APIRouter(tags=["annotations"])


@router.post("/")
@_catch
async def create_annotation(
        article_id: int = Body(...), content: str = Body(...),
        position: Optional[dict] = Body(None),
        selection_text: Optional[str] = Body(None),
        parent_id: Optional[int] = Body(None),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session)
):
    """创建批注"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        return fail("文章不存在")

    if parent_id:
        parent = await db.scalar(select(ArticleAnnotation).where(ArticleAnnotation.id == parent_id))
        if not parent:
            return fail("父批注不存在")
        if parent.article != article_id:
            return fail("父批注不属于该文章")

    ann = ArticleAnnotation(article=article_id, user=current_user.id, parent=parent_id,
                            content=content, position=str(position) if position else None,
                            selection_text=selection_text, is_resolved=False,
                            created_at=datetime.now(), updated_at=datetime.now())
    db.add(ann)
    await db.commit()
    await db.refresh(ann)

    user = await db.scalar(select(User).where(User.id == current_user.id))
    return ok(data=_fmt_ann(ann, {current_user.id: user} if user else {}))


@router.get("/article/{article_id}")
@_catch
async def get_article_annotations(article_id: int, resolved: Optional[bool] = Query(None),
                                   current_user=Depends(jwt_required),
                                   db: AsyncSession = Depends(get_async_session)):
    """获取文章的批注（树形结构）"""
    q = select(ArticleAnnotation).where(ArticleAnnotation.article == article_id)
    if resolved is not None:
        q = q.where(ArticleAnnotation.is_resolved == resolved)
    q = q.order_by(ArticleAnnotation.created_at.asc())

    anns = (await db.execute(q)).scalars().all()
    uids = {a.user for a in anns}
    users = {u.id: u for u in (await db.execute(select(User).where(User.id.in_(uids)))).scalars().all()}

    by_id, roots = {}, []
    for ann in anns:
        d = _fmt_ann(ann, users)
        d['replies'] = []
        by_id[ann.id] = d
        (roots if ann.parent is None else by_id.get(ann.parent, {}).get('replies', [])).append(d)

    return ok(data={'annotations': roots, 'count': len(roots)})


@router.put("/{annotation_id}")
@_catch
async def update_annotation(annotation_id: int, content: Optional[str] = Body(None),
                             is_resolved: Optional[bool] = Body(None),
                             current_user=Depends(jwt_required),
                             db: AsyncSession = Depends(get_async_session)):
    """更新批注（仅本人或管理员）"""
    ann = await db.scalar(select(ArticleAnnotation).where(ArticleAnnotation.id == annotation_id))
    if not ann:
        return fail("批注不存在")
    is_admin = getattr(current_user, 'is_superuser', False)
    if ann.user != current_user.id and not is_admin:
        return fail("无权修改此批注")

    if content is not None:
        ann.content = content
    if is_resolved is not None:
        ann.is_resolved = is_resolved
    ann.updated_at = datetime.now()
    await db.commit()
    return ok(msg="批注更新成功")


@router.delete("/{annotation_id}")
@_catch
async def delete_annotation(annotation_id: int, current_user=Depends(jwt_required),
                             db: AsyncSession = Depends(get_async_session)):
    """删除批注（仅本人或管理员）"""
    ann = await db.scalar(select(ArticleAnnotation).where(ArticleAnnotation.id == annotation_id))
    if not ann:
        return fail("批注不存在")
    is_admin = getattr(current_user, 'is_superuser', False)
    if ann.user != current_user.id and not is_admin:
        return fail("无权删除此批注")
    await db.delete(ann)
    await db.commit()
    return ok(msg="批注删除成功")
