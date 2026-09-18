"""comment 模块业务逻辑

公开读过滤隐私字段；回复树在应用层按 ``parent_id`` 组装；删除评论时级联删除其回复。
"""

from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.comment.comment import Comment
from shared.models.comment.comment_vote import CommentVote
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.content.comment.crud import comment_crud
from src.api.v3.modules.content.comment.schema import CommentCreate

logger = get_logger("comment")


def to_admin_out(comment: Comment) -> dict:
    """管理端字段（含隐私与审核信息）"""
    spam_score = comment.spam_score
    return {
        "id": comment.id,
        "article_id": comment.article_id,
        "parent_id": comment.parent_id,
        "user_id": comment.user_id,
        "content": comment.content,
        "author_name": comment.author_name,
        "author_email": comment.author_email,
        "author_url": comment.author_url,
        "author_ip": comment.author_ip,
        "user_agent": comment.user_agent,
        "is_approved": bool(comment.is_approved),
        "likes": comment.likes or 0,
        "spam_score": float(spam_score) if spam_score is not None else None,
        "spam_reasons": comment.spam_reasons,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }


def to_public_out(comment: Comment) -> dict:
    """公开字段：**不暴露** author_email / author_ip / user_agent"""
    return {
        "id": comment.id,
        "article_id": comment.article_id,
        "parent_id": comment.parent_id,
        "user_id": comment.user_id,
        "content": comment.content,
        "author_name": comment.author_name,
        "author_url": comment.author_url,
        "likes": comment.likes or 0,
        "created_at": comment.created_at,
        "children": [],
    }


def build_tree(items: Sequence[dict]) -> List[dict]:
    """按 ``parent_id`` 组装回复树（按时间正序）"""
    by_id = {item["id"]: item for item in items}
    roots: List[dict] = []
    for item in by_id.values():
        parent = by_id.get(item["parent_id"]) if item["parent_id"] else None
        if parent is not None and parent["id"] != item["id"]:
            parent["children"].append(item)
        else:
            roots.append(item)

    def _sort(nodes: List[dict]) -> List[dict]:
        nodes.sort(key=lambda node: (node.get("created_at") or datetime.min, node["id"]))
        for node in nodes:
            _sort(node["children"])
        return nodes

    return _sort(roots)


class CommentService:
    """评论管理"""

    async def list_comments(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        article_id: Optional[int] = None,
        user_id: Optional[int] = None,
        is_approved: Optional[bool] = None,
        order_by: Optional[str] = None,
        order: str = "desc",
    ) -> Tuple[List[dict], int]:
        items, total = await comment_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"article_id": article_id, "user_id": user_id, "is_approved": is_approved},
            order_by=order_by or "id",
            order=order,
        )
        return [to_admin_out(comment) for comment in items], total

    async def list_pending(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20
    ) -> Tuple[List[dict], int]:
        return await self.list_comments(db, page=page, page_size=page_size, is_approved=False)

    async def get_comment(self, db: AsyncSession, comment_id: int) -> dict:
        comment = await comment_crud.get(db, comment_id)
        if comment is None:
            raise NotFoundError("评论不存在")
        return to_admin_out(comment)

    async def create_comment(
        self,
        db: AsyncSession,
        payload: CommentCreate,
        *,
        user=None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        if await db.scalar(select(Article.id).where(Article.id == payload.article_id)) is None:
            raise NotFoundError("目标文章不存在")
        if payload.parent_id is not None:
            parent = await comment_crud.get(db, payload.parent_id)
            if parent is None or parent.article_id != payload.article_id:
                raise NotFoundError("父评论不存在或不属于该文章")

        now = datetime.now()
        comment = await comment_crud.create(
            db,
            {
                "article_id": payload.article_id,
                "parent_id": payload.parent_id,
                "content": payload.content,
                "author_name": payload.author_name or getattr(user, "username", None),
                "author_email": payload.author_email
                                or (getattr(user, "email", None) if user is not None else None),
                "author_url": payload.author_url,
                "user_id": getattr(user, "id", None),
                "author_ip": ip,
                "user_agent": user_agent,
                "is_approved": True,
                "likes": 0,
                "created_at": now,
                "updated_at": now,
            },
        )
        return to_public_out(comment)

    async def set_approved(self, db: AsyncSession, comment_id: int, approved: bool) -> dict:
        comment = await comment_crud.get(db, comment_id)
        if comment is None:
            raise NotFoundError("评论不存在")
        comment = await comment_crud.update(
            db, comment, {"is_approved": approved, "updated_at": datetime.now()}
        )
        return to_admin_out(comment)

    async def update_comment(self, db: AsyncSession, comment_id: int, content: str) -> dict:
        comment = await comment_crud.get(db, comment_id)
        if comment is None:
            raise NotFoundError("评论不存在")
        comment = await comment_crud.update(
            db, comment, {"content": content, "updated_at": datetime.now()}
        )
        return to_admin_out(comment)

    async def delete_comment(self, db: AsyncSession, comment_id: int) -> None:
        """删除评论，并级联删除其全部回复（``parent_id`` 无外键级联）"""
        comment = await comment_crud.get(db, comment_id)
        if comment is None:
            raise NotFoundError("评论不存在")
        await self._delete_descendants(db, comment_id)
        await comment_crud.remove(db, comment)

    async def _delete_descendants(self, db: AsyncSession, comment_id: int) -> int:
        children = list(
            (await db.execute(select(Comment).where(Comment.parent_id == comment_id)))
            .scalars()
            .all()
        )
        deleted = 0
        for child in children:
            deleted += await self._delete_descendants(db, child.id)
            await db.delete(child)
            deleted += 1
        if deleted:
            await db.commit()
        return deleted

    async def batch_delete(self, db: AsyncSession, ids: Sequence[int]) -> int:
        count = 0
        for comment_id in ids:
            try:
                await self.delete_comment(db, comment_id)
                count += 1
            except NotFoundError:
                continue
        return count

    async def toggle_like(self, db: AsyncSession, *, comment_id: int, user_id: int) -> dict:
        """点赞 / 取消点赞（幂等切换）

        注意：legacy 的移动端点赞接口引用了**不存在的** ``CommentLike`` 类（项目里只有
        ``CommentVote`` / ``comment_votes``），因此那条路径必然 NameError。这里用真实模型实现。
        """
        comment = await comment_crud.get(db, comment_id)
        if comment is None:
            raise NotFoundError("评论不存在")

        existing = await db.scalar(
            select(CommentVote).where(
                CommentVote.comment_id == comment_id, CommentVote.user == user_id
            )
        )
        if existing is not None:
            await db.delete(existing)
            comment.likes = max(0, (comment.likes or 0) - 1)
            liked = False
        else:
            db.add(CommentVote(comment_id=comment_id, user=user_id))
            comment.likes = (comment.likes or 0) + 1
            liked = True

        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return {"comment_id": comment_id, "liked": liked, "likes": comment.likes or 0}

    async def article_tree(
        self, db: AsyncSession, article_id: int, *, approved_only: bool = True
    ) -> List[dict]:
        """某文章的公开评论树"""
        stmt = select(Comment).where(Comment.article_id == article_id)
        if approved_only:
            stmt = stmt.where(Comment.is_approved.is_(True))
        stmt = stmt.order_by(Comment.created_at.asc(), Comment.id.asc())
        comments = list((await db.execute(stmt)).scalars().all())
        return build_tree([to_public_out(comment) for comment in comments])


comment_service = CommentService()
