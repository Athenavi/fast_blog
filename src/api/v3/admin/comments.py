"""
V3 评论管理 API

权限要求:
  GET    /comments/pending       → comment:view
  POST   /comments/{id}/approve  → comment:approve
  POST   /comments/{id}/reject   → comment:approve
  DELETE /comments/{id}          → comment:delete
  GET    /comments/spam-config   → settings:view
  PUT    /comments/spam-config   → settings:edit
"""
import logging

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.comment import Comment
from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db, get_current_user
from src.api.v3._permission import Permission
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-comments"])


@router.get("/comments/pending", summary="待审核评论")
async def pending_comments(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("comment:view")),
):
    result = await db.execute(
        select(Comment).where(Comment.is_approved == False)
        .order_by(Comment.created_at.desc())
    )
    comments = result.scalars().all()
    return ApiResponse(success=True, data={
        "comments": [_cvt(c) for c in comments],
        "total": len(comments),
    })


@router.post("/comments/{comment_id}/approve", summary="审核通过")
async def approve_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("comment:approve")),
):
    comment = await db.get(Comment, comment_id)
    if not comment:
        return ApiResponse(success=False, error="评论不存在")
    comment.is_approved = True
    await db.commit()
    return ApiResponse(success=True, message="评论已审核通过")


@router.post("/comments/{comment_id}/reject", summary="驳回评论")
async def reject_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("comment:approve")),
):
    comment = await db.get(Comment, comment_id)
    if not comment:
        return ApiResponse(success=False, error="评论不存在")
    await db.delete(comment)
    await db.commit()
    return ApiResponse(success=True, message="评论已驳回删除")


@router.delete("/comments/{comment_id}", summary="删除评论")
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(Permission("comment:delete")),
):
    comment = await db.get(Comment, comment_id)
    if not comment:
        return ApiResponse(success=False, error="评论不存在")
    await db.delete(comment)
    await db.commit()
    return ApiResponse(success=True, message="评论已删除")


def _cvt(c: Comment) -> dict:
    return {
        "id": c.id,
        "article_id": c.article_id,
        "user_id": c.user_id,
        "content": c.content[:200] if c.content else "",
        "is_approved": c.is_approved,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
