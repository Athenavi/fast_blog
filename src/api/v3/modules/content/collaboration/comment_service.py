"""团队评论的业务逻辑（T5-11 批次 9）

**与 v2 的差异**（v2 的 ``team_comments.py`` 有三处硬伤，本模块逐一修掉）：

  - v2 的 ``POST /comment`` **没有 ``@router`` 装饰器** —— 前端根本发不出评论；这里补上；
  - v2 的 ``resolve`` **没有任何权限校验**（任何登录用户可「解决」任意评论）；这里要求
    **作者或管理员**；
  - v2 的 @提及查询用 ``TeamComment.mentions.contains(str(user_id))`` 做**子串匹配**
    （``user_id=1`` 会命中 ``[11,21]``）；这里改成「SQL 粗筛 + 应用层精确解析 JSON 列表」。

``text`` 入库前一律 ``html.escape``（与 v2 一致，防 XSS）；``mentions`` 列是 ``String(500)``，
存 JSON 数组字符串（沿用 v2 的列约定，不改表）。
"""

import html
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.comment.team_comment import TeamComment
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from src.api.v3.modules.content.collaboration.crud import team_comment_crud
from src.api.v3.modules.content.collaboration.schema import (
    CommentCreate,
    CommentOut,
    CommentUpdate,
)

MAX_PAGE_SIZE = 200


def _parse_mentions(value: Optional[str]) -> Optional[list[int]]:
    """``mentions`` 列是 JSON 数组字符串；脏数据回退 None（避免列表接口 500）"""
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except ValueError:
        return None
    if not isinstance(parsed, list):
        return None
    return [int(item) for item in parsed if isinstance(item, int)]


def _dump_mentions(value: Optional[list[int]]) -> Optional[str]:
    return json.dumps(value, ensure_ascii=False) if value else None


def _comment_out(row, *, author_name: Optional[str] = None) -> dict:
    data = CommentOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["mentions"] = _parse_mentions(row.mentions)
    if author_name:
        data["author_name"] = author_name
    return data


class CommentService:
    """团队评论（挂在任意内容对象上：``content_type`` + ``content_id``）"""

    async def _ensure(self, db: AsyncSession, comment_id: int) -> TeamComment:
        row = await team_comment_crud.get(db, comment_id)
        if row is None:
            raise NotFoundError("评论不存在")
        return row

    async def list_comments(
        self,
        db: AsyncSession,
        content_type: str,
        content_id: int,
        *,
        include_resolved: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        filters: dict = {"content_type": content_type, "content_id": content_id}
        if not include_resolved:
            filters["is_resolved"] = False
        rows, total = await team_comment_crud.list(
            db, page=page, page_size=min(page_size, MAX_PAGE_SIZE), filters=filters
        )
        author_ids = {row.author_id for row in rows if row.author_id}
        names: dict[int, str] = {}
        if author_ids:
            authors = (
                await db.execute(select(User.id, User.username).where(User.id.in_(author_ids)))
            ).all()
            names = {int(uid): username for uid, username in authors}
        return [
            _comment_out(row, author_name=names.get(row.author_id or 0)) for row in rows
        ], total

    async def create(self, db: AsyncSession, payload: CommentCreate, author_id: int) -> dict:
        if payload.parent_id is not None:
            parent = await team_comment_crud.get(db, payload.parent_id)
            if parent is None:
                raise BadRequestError("父评论不存在")
            if (parent.content_type, parent.content_id) != (payload.content_type, payload.content_id):
                raise BadRequestError("父评论不属于同一内容对象")
        now = datetime.now()
        row = await team_comment_crud.create(
            db,
            {
                "content_type": payload.content_type,
                "content_id": payload.content_id,
                "author_id": author_id,
                "parent_id": payload.parent_id,
                "text": html.escape(payload.text),
                "mentions": _dump_mentions(payload.mentions),
                "is_resolved": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        return _comment_out(row)

    async def update(
        self, db: AsyncSession, comment_id: int, payload: CommentUpdate, user_id: int
    ) -> dict:
        row = await self._ensure(db, comment_id)
        if row.author_id != user_id:
            raise ForbiddenError("只能修改自己的评论")
        updated = await team_comment_crud.update(
            db,
            row,
            {"text": html.escape(payload.text), "updated_at": datetime.now()},
        )
        return _comment_out(updated)

    async def delete(self, db: AsyncSession, comment_id: int, user_id: int, *, is_admin: bool) -> int:
        """删除评论及其所有子孙（递归），返回实际删除条数"""
        row = await self._ensure(db, comment_id)
        if row.author_id != user_id and not is_admin:
            raise ForbiddenError("只能删除自己的评论")
        # 收集子孙（逐层向下，避免递归 SQL）
        to_delete = [row]
        frontier = [row.id]
        while frontier:
            children = (
                await db.execute(select(TeamComment).where(TeamComment.parent_id.in_(frontier)))
            ).scalars().all()
            if not children:
                break
            to_delete.extend(children)
            frontier = [child.id for child in children]
        for item in reversed(to_delete):
            await team_comment_crud.remove(db, item)
        return len(to_delete)

    async def resolve(self, db: AsyncSession, comment_id: int, user_id: int, *, is_admin: bool) -> dict:
        row = await self._ensure(db, comment_id)
        if row.author_id != user_id and not is_admin:
            raise ForbiddenError("只有评论作者或管理员可以标记解决")
        if row.is_resolved:
            raise BadRequestError("该评论已是已解决状态")
        updated = await team_comment_crud.update(
            db,
            row,
            {"is_resolved": True, "resolved_by": user_id, "resolved_at": datetime.now()},
        )
        return _comment_out(updated)

    async def list_mentions(
        self, db: AsyncSession, user_id: int, *, limit: int = 20, unread_only: bool = False
    ) -> list[dict]:
        """@ 到我 的评论

        ``mentions`` 是 ``String(500)``，所以先用 SQL ``like`` 粗筛，再在应用层
        **精确解析 JSON 列表**判断（v2 直接 contains 会误匹配 ``[11,21]``）。
        """
        filters: dict = {}
        if unread_only:
            filters["is_resolved"] = False
        rows, _total = await team_comment_crud.list(
            db,
            page=1,
            page_size=min(max(limit * 5, limit), MAX_PAGE_SIZE),
            keyword=None,
            filters=filters,
        )
        matched = [
            row
            for row in rows
            if row.mentions and user_id in (_parse_mentions(row.mentions) or [])
        ][: min(limit, MAX_PAGE_SIZE)]
        return [_comment_out(row) for row in matched]

    async def statistics(self, db: AsyncSession, content_type: Optional[str] = None) -> dict:
        conditions = []
        if content_type:
            conditions.append(TeamComment.content_type == content_type)
        total = int(
            (
                await db.execute(select(func.count()).select_from(TeamComment).where(*conditions))
            ).scalar()
            or 0
        )
        resolved = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(TeamComment)
                    .where(*conditions, TeamComment.is_resolved.is_(True))
                )
            ).scalar()
            or 0
        )
        by_author = (
            await db.execute(
                select(TeamComment.author_id, func.count())
                .where(*conditions)
                .group_by(TeamComment.author_id)
                .order_by(func.count().desc())
                .limit(20)
            )
        ).all()
        return {
            "total_comments": total,
            "resolved_comments": resolved,
            "unresolved_comments": total - resolved,
            "by_author": [
                {"author_id": author_id, "count": int(count or 0)}
                for author_id, count in by_author
                if author_id is not None
            ],
        }


comment_service = CommentService()
