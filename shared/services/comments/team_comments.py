"""
团队评论和反馈服务（数据库持久化）

提供内部评论、@提及、评论线程等功能
支持团队协作和内容反馈
使用 TeamComment ORM 模型持久化到数据库
"""

import html
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.comment import TeamComment
from src.unified_logger import default_logger as logger


class TeamCommentService:
    """
    团队评论和反馈服务
    
    管理团队内部的评论和反馈（数据库持久化）
    """

    async def create_comment(
            self,
            db: AsyncSession,
            content_id: int,
            content_type: str,
            author_id: int,
            author_name: str,
            text: str,
            parent_id: Optional[int] = None,
            mentions: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        创建评论

        Args:
            db: 数据库会话
            content_id: 内容ID
            content_type: 内容类型
            author_id: 作者ID
            author_name: 作者名称
            text: 评论内容
            parent_id: 父评论ID（用于回复）
            mentions: @提及的用户ID列表

        Returns:
            创建的评论
        """
        now = datetime.now(timezone.utc)
        mention_str = json.dumps(mentions) if mentions else None

        comment = TeamComment(
            content_type=content_type,
            content_id=content_id,
            author_id=author_id,
            parent_id=parent_id,
            text=html.escape(text),
            mentions=mention_str,
            is_resolved=False,
            created_at=now,
            updated_at=None,
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)

        result = comment.to_dict()
        result['replies'] = []
        result['author_name'] = author_name
        return result

    async def update_comment(
            self,
            db: AsyncSession,
            comment_id: int,
            author_id: int,
            text: str
    ) -> Dict[str, Any]:
        """
        更新评论

        Args:
            db: 数据库会话
            comment_id: 评论ID
            author_id: 作者ID
            text: 新的评论内容

        Returns:
            更新后的评论
        """
        result = await db.execute(
            select(TeamComment).where(TeamComment.id == comment_id)
        )
        comment = result.scalar_one_or_none()

        if not comment:
            raise ValueError(f"Comment {comment_id} not found")

        if comment.author_id != author_id:
            raise ValueError("Only the author can update the comment")

        comment.text = html.escape(text)
        comment.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(comment)

        return comment.to_dict()

    async def delete_comment(
            self,
            db: AsyncSession,
            comment_id: int,
            user_id: int,
            is_admin: bool = False
    ) -> bool:
        """
        删除评论

        Args:
            db: 数据库会话
            comment_id: 评论ID
            user_id: 用户ID
            is_admin: 是否是管理员

        Returns:
            是否删除成功
        """
        result = await db.execute(
            select(TeamComment).where(TeamComment.id == comment_id)
        )
        comment = result.scalar_one_or_none()

        if not comment:
            return False

        # 只有作者或管理员可以删除
        if comment.author_id != user_id and not is_admin:
            raise ValueError("Only the author or admin can delete the comment")

        # 递归删除子评论
        await self._delete_comment_recursive(db, comment_id)

        # 删除自身
        await db.delete(comment)
        await db.commit()
        return True

    async def resolve_comment(
            self,
            db: AsyncSession,
            comment_id: int,
            resolver_id: int,
            resolver_name: str
    ) -> Dict[str, Any]:
        """
        标记评论为已解决

        Args:
            db: 数据库会话
            comment_id: 评论ID
            resolver_id: 解决者ID
            resolver_name: 解决者名称

        Returns:
            更新后的评论
        """
        result = await db.execute(
            select(TeamComment).where(TeamComment.id == comment_id)
        )
        comment = result.scalar_one_or_none()

        if not comment:
            raise ValueError(f"Comment {comment_id} not found")

        comment.is_resolved = True
        comment.resolved_by = resolver_id
        comment.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(comment)

        return comment.to_dict()

    async def get_comments_for_content(
            self,
            db: AsyncSession,
            content_id: int,
            content_type: str,
            include_resolved: bool = True,
            page: int = 1,
            per_page: int = 50
    ) -> Dict[str, Any]:
        """
        获取内容的评论（支持分页，批量加载回复避免 N+1）

        Args:
            db: 数据库会话
            content_id: 内容ID
            content_type: 内容类型
            include_resolved: 是否包含已解决的评论
            page: 页码
            per_page: 每页数量

        Returns:
            包含评论列表和分页信息的字典
        """
        # 查询顶级评论总数
        count_query = select(func.count(TeamComment.id)).where(
            TeamComment.content_id == content_id,
            TeamComment.content_type == content_type,
            TeamComment.parent_id.is_(None)
        )
        if not include_resolved:
            count_query = count_query.where(TeamComment.is_resolved == False)
        total = (await db.execute(count_query)).scalar() or 0

        # 查询顶级评论（分页）
        query = select(TeamComment).where(
            TeamComment.content_id == content_id,
            TeamComment.content_type == content_type,
            TeamComment.parent_id.is_(None)
        )
        if not include_resolved:
            query = query.where(TeamComment.is_resolved == False)
        query = query.order_by(TeamComment.created_at.asc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await db.execute(query)
        top_level = result.scalars().all()

        if not top_level:
            return {
                "comments": [],
                "pagination": {"page": page, "per_page": per_page, "total": 0, "total_pages": 0}
            }

        # 批量加载所有顶级评论的回复（避免 N+1）
        top_level_ids = [c.id for c in top_level]
        replies_result = await db.execute(
            select(TeamComment)
            .where(TeamComment.parent_id.in_(top_level_ids))
            .order_by(TeamComment.created_at.asc())
        )
        all_replies = replies_result.scalars().all()

        # 将回复按 parent_id 分组
        replies_by_parent: Dict[int, List[Dict[str, Any]]] = {}
        for reply in all_replies:
            replies_by_parent.setdefault(reply.parent_id, []).append(reply.to_dict())

        comments = []
        for c in top_level:
            comment_dict = c.to_dict()
            comment_dict['replies_data'] = replies_by_parent.get(c.id, [])
            comments.append(comment_dict)

        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            "comments": comments,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }
        }

    async def get_user_mentions(
            self,
            db: AsyncSession,
            user_id: int,
            unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取用户的@提及

        Args:
            db: 数据库会话
            user_id: 用户ID
            unread_only: 是否只返回未读的

        Returns:
            提及列表
        """
        # 查询 mentions 字段包含该 user_id 的评论
        user_id_str = str(user_id)
        query = select(TeamComment).where(
            TeamComment.mentions.isnot(None),
            TeamComment.mentions.contains(user_id_str)
        ).order_by(TeamComment.created_at.desc())

        result = await db.execute(query)
        comments = result.scalars().all()

        return [c.to_dict() for c in comments]

    async def get_statistics(
            self,
            db: AsyncSession,
            content_id: Optional[int] = None,
            content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取评论统计

        Args:
            db: 数据库会话
            content_id: 内容ID过滤
            content_type: 内容类型过滤

        Returns:
            统计信息
        """
        query = select(TeamComment)

        if content_id:
            query = query.where(TeamComment.content_id == content_id)
        if content_type:
            query = query.where(TeamComment.content_type == content_type)

        result = await db.execute(query)
        all_comments = result.scalars().all()

        total = len(all_comments)
        resolved = sum(1 for c in all_comments if c.is_resolved)
        unresolved = total - resolved

        # 统计每个作者的评论数（按 author_id）
        by_author = {}
        for comment in all_comments:
            author_key = str(comment.author_id)
            by_author[author_key] = by_author.get(author_key, 0) + 1

        return {
            'total_comments': total,
            'resolved_comments': resolved,
            'unresolved_comments': unresolved,
            'by_author': by_author,
        }

    async def _delete_comment_recursive(self, db: AsyncSession, parent_id: int):
        """递归删除子评论"""
        result = await db.execute(
            select(TeamComment).where(TeamComment.parent_id == parent_id)
        )
        children = result.scalars().all()

        for child in children:
            # 递归删除孙评论
            await self._delete_comment_recursive(db, child.id)
            await db.delete(child)

    async def _get_replies(self, db: AsyncSession, parent_id: int) -> List[Dict[str, Any]]:
        """获取评论的回复"""
        result = await db.execute(
            select(TeamComment)
            .where(TeamComment.parent_id == parent_id)
            .order_by(TeamComment.created_at.asc())
        )
        replies = result.scalars().all()
        return [r.to_dict() for r in replies]


# 全局实例
team_comment_service = TeamCommentService()

# 导出
__all__ = ['TeamCommentService', 'team_comment_service']
