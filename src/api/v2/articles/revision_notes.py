"""
文章修订注释 API
"""
from datetime import datetime, timezone
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import ArticleRevisionNote
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


router = APIRouter(tags=["revision-notes"])


class CreateNoteRequest(BaseModel):
    revision_id: int
    note_content: str


class UpdateNoteRequest(BaseModel):
    note_content: str


@router.post("/notes")
@_catch
async def create_revision_note(req: CreateNoteRequest, current_user=Depends(jwt_required),
                                db: AsyncSession = Depends(get_async_db)):
    """为修订版本添加注释"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    note = ArticleRevisionNote(
        revision_id=req.revision_id,
        user_id=current_user.id,
        note_content=req.note_content,
        created_at=now,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return ok(data={"note": {"id": note.id, "revision_id": note.revision_id, "note_content": note.note_content, "created_at": note.created_at.isoformat() if note.created_at else None}})


@router.get("/notes/{revision_id}")
@_catch
async def list_revision_notes(revision_id: int, current_user=Depends(jwt_required),
                               db: AsyncSession = Depends(get_async_db)):
    """获取修订版本的所有注释"""
    result = await db.execute(
        select(ArticleRevisionNote)
        .where(ArticleRevisionNote.revision_id == revision_id)
        .order_by(ArticleRevisionNote.created_at.asc())
    )
    notes = result.scalars().all()
    return ok(data=[{
        "id": n.id, "revision_id": n.revision_id, "user_id": n.user_id,
        "note_content": n.note_content,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    } for n in notes])


@router.put("/notes/{note_id}")
@_catch
async def update_revision_note(note_id: int, req: UpdateNoteRequest,
                                current_user=Depends(jwt_required),
                                db: AsyncSession = Depends(get_async_db)):
    """更新注释"""
    note = await db.get(ArticleRevisionNote, note_id)
    if not note:
        return fail("注释不存在")
    if note.user_id != current_user.id:
        return fail("无权修改此注释")
    note.note_content = req.note_content
    await db.commit()
    return ok(msg="注释已更新")


@router.delete("/notes/{note_id}")
@_catch
async def delete_revision_note(note_id: int, current_user=Depends(jwt_required),
                                db: AsyncSession = Depends(get_async_db)):
    """删除注释"""
    note = await db.get(ArticleRevisionNote, note_id)
    if not note:
        return fail("注释不存在")
    if note.user_id != current_user.id:
        return fail("无权删除此注释")
    await db.delete(note)
    await db.commit()
    return ok(msg="注释已删除")


@router.get("/notes/user/{user_id}")
@_catch
async def list_user_revision_notes(user_id: int, current_user=Depends(jwt_required),
                                    db: AsyncSession = Depends(get_async_db)):
    """获取用户的所有修订注释"""
    result = await db.execute(
        select(ArticleRevisionNote)
        .where(ArticleRevisionNote.user_id == user_id)
        .order_by(ArticleRevisionNote.created_at.desc())
    )
    notes = result.scalars().all()
    return ok(data=[{
        "id": n.id, "revision_id": n.revision_id, "user_id": n.user_id,
        "note_content": n.note_content,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    } for n in notes])
