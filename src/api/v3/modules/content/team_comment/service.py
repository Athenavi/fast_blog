"""team_comment 模块业务逻辑（团队 / 内部评论：评论树、@提及、解决、统计）

落点表：既有 ``team_comments``（``TeamComment``）。DDL / 列名见模块 ``__init__.py``。
本文件把**纯函数**（不碰 DB / 时钟 / FastAPI，可单测）与 **DB 操作**（``TeamCommentService``）
分开，纯函数供 ``_pending_test_team_comment.py`` 直接断言。

与 v2（``shared/services/comments/team_comments.py``）的差异、未接线项、职责边界，
均在模块 ``__init__.py`` 中集中说明；此处只补一处实现要点：

  - ``mentions`` 列是 ``String(500)`` 里存的 JSON 数组字符串（沿用既有列约定，不改表）；
    读取时用 ``parse_mentions`` **精确解析**，写入时用 ``dump_mentions`` 归一化（去重 / 升序 / 裁剪）。
"""

import html
import json
from collections import Counter
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.comment.team_comment import TeamComment
from shared.models.user import User
from src.api.v3.core.base_crud import CRUDBase
from src.api.v3.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.content.team_comment.schema import (
    MENTIONS_MAX_LENGTH,
    TeamCommentCreate,
    TeamCommentUpdate,
)

logger = get_logger("content.team_comment")

MAX_PAGE_SIZE = 200


# ============================================================ DB 访问层（唯一 DB 入口）
class TeamCommentCRUD(CRUDBase[TeamComment, dict, dict]):
    model = TeamComment
    keyword_fields = ("text",)
    #: 评论以创建时间为序（默认新在前；线程树另行按 asc 排序）
    default_order_by = "created_at"


team_comment_crud = TeamCommentCRUD()


# ============================================================ 纯函数（可单测，无 DB / 时钟依赖）
def parse_mentions(value: Optional[str]) -> list[int]:
    """把 ``team_comments.mentions``（JSON 数组字符串）解析成整数列表（**纯函数**）

    - 空值 / 非法 JSON / 非数组 → ``[]``（脏数据不至于让列表接口 500）
    - 排除 ``bool``（``True`` 是 ``int`` 子类，不应被当成 ``1``）
    - 同时接受 JSON 里的 int 与「数字字符串」（``"3"``）
    """
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    result: list[int] = []
    for item in parsed:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            result.append(int(item))
        elif isinstance(item, str) and item.strip().lstrip("+-").isdigit():
            result.append(int(item.strip()))
    return result


def dump_mentions(user_ids: Optional[Sequence[int]]) -> Optional[str]:
    """把用户 ID 列表序列化为 ``mentions`` 列字符串（**纯函数**）

    - 只保留**正整数** int（过滤 bool / 负数 / 零 / 非 int）
    - 去重后**升序**写出，保证可比较、可搜索
    - 空结果 → ``None``（DB 写 NULL）
    - 结果超过 ``MENTIONS_MAX_LENGTH`` 时逐步舍弃尾部成员，直到落回列宽
    """
    if not user_ids:
        return None
    normalized = sorted(
        {
            int(uid)
            for uid in user_ids
            if isinstance(uid, int) and not isinstance(uid, bool) and int(uid) > 0
        }
    )
    if not normalized:
        return None
    while normalized and len(json.dumps(normalized)) > MENTIONS_MAX_LENGTH:
        normalized.pop()
    return json.dumps(normalized) if normalized else None


def _thread_sort_key(node: dict) -> tuple:
    """线程排序键：创建时间升序（``None`` 视作最早），同刻按 id 升序（**纯函数**）"""
    created = node.get("created_at")
    return (created is None, "" if created is None else str(created), int(node.get("id") or 0))


def build_threads(rows: Sequence[dict]) -> list[dict]:
    """把扁平的评论行按 ``parent_id`` 组装成线程树（**纯函数**）

    每行须含 ``id`` / ``parent_id``（其余字段原样保留）。返回顶层节点列表，每个节点追加
    ``children``（递归排序，规则见 ``_thread_sort_key``）。父节点不在本批数据里的**孤儿节点会
    被提升为顶层**，避免分页截断时丢评论。假定 ``parent_id`` 指向先创建的行（写入时已校验父评论
    存在），故不存在环。
    """
    nodes: dict[int, dict] = {}
    for row in rows:
        node = dict(row)
        node["children"] = []
        nodes[int(node["id"])] = node

    roots: list[dict] = []
    for node in nodes.values():
        parent_id = node.get("parent_id")
        parent = nodes.get(int(parent_id)) if parent_id is not None else None
        if parent is not None and parent is not node:
            parent["children"].append(node)
        else:
            roots.append(node)

    def _sort(items: list[dict]) -> None:
        items.sort(key=_thread_sort_key)
        for item in items:
            _sort(item["children"])

    _sort(roots)
    return roots


def summarize(rows: Sequence[dict]) -> dict:
    """统计评论（**纯函数**）：总数 / 已解决 / 未解决 / 各作者计数

    ``by_author`` 仅统计 ``author_id`` 非空的行，按计数降序、``author_id`` 升序打破并列。
    """
    total = len(rows)
    resolved = sum(1 for row in rows if row.get("is_resolved"))
    counter: Counter = Counter(
        int(row["author_id"]) for row in rows if row.get("author_id") is not None
    )
    by_author = [
        {"author_id": author_id, "count": count}
        for author_id, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return {
        "total_comments": total,
        "resolved_comments": resolved,
        "unresolved_comments": total - resolved,
        "by_author": by_author,
    }


def _row_to_dict(row: TeamComment, *, author_name: Optional[str] = None) -> dict:
    """ORM 行 → 输出 dict（``mentions`` 顺手解析成整数列表，``children`` 预置空列表）"""
    return {
        "id": row.id,
        "content_type": row.content_type,
        "content_id": row.content_id,
        "author_id": row.author_id,
        "author_name": author_name,
        "parent_id": row.parent_id,
        "text": row.text,
        "mentions": parse_mentions(row.mentions),
        "is_resolved": bool(row.is_resolved),
        "resolved_by": row.resolved_by,
        "resolved_at": row.resolved_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "children": [],
    }


async def _author_names(db: AsyncSession, author_ids: set[int]) -> dict[int, str]:
    """批量取作者名（避免 N+1）"""
    if not author_ids:
        return {}
    pairs = (
        await db.execute(select(User.id, User.username).where(User.id.in_(author_ids)))
    ).all()
    return {int(uid): username for uid, username in pairs}


class TeamCommentService:
    """团队 / 内部评论"""

    async def _ensure(self, db: AsyncSession, comment_id: int) -> TeamComment:
        row = await team_comment_crud.get(db, comment_id)
        if row is None:
            raise NotFoundError("评论不存在")
        return row

    @staticmethod
    def _assert_can_write(row: TeamComment, *, user_id: int, is_admin: bool, action: str) -> None:
        """写操作的**真实授权**：仅评论作者本人或管理员（v2 的 resolve 缺此校验）"""
        if row.author_id != user_id and not is_admin:
            raise ForbiddenError(f"只有评论作者或管理员可以{action}该评论")

    # ------------------------------------------------------------ 读
    async def list_for_content(
        self,
        db: AsyncSession,
        content_type: str,
        content_id: int,
        *,
        include_resolved: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        """某内容对象的评论**线程树**（顶层评论分页，子回复批量加载避免 N+1）

        ``include_resolved=False`` 时过滤掉「已解决」的**顶层**评论（与 v2 一致，只作用于顶层）。
        """
        filters: dict = {
            "content_type": content_type,
            "content_id": content_id,
            "parent_id": None,
        }
        if not include_resolved:
            filters["is_resolved"] = False
        roots, total = await team_comment_crud.list(
            db,
            page=page,
            page_size=min(page_size, MAX_PAGE_SIZE),
            filters=filters,
            order_by="created_at",
            order="asc",
        )
        if not roots:
            return [], total

        root_ids = [row.id for row in roots]
        replies = (
            await db.execute(
                select(TeamComment)
                .where(TeamComment.parent_id.in_(root_ids))
                .order_by(TeamComment.created_at.asc(), TeamComment.id.asc())
            )
        ).scalars().all()

        author_ids = {row.author_id for row in (*roots, *replies) if row.author_id}
        names = await _author_names(db, author_ids)
        rows = [
            _row_to_dict(row, author_name=names.get(row.author_id or 0))
            for row in (*roots, *replies)
        ]
        return build_threads(rows), total

    async def get(self, db: AsyncSession, comment_id: int) -> dict:
        row = await self._ensure(db, comment_id)
        names = await _author_names(db, {row.author_id} if row.author_id else set())
        return _row_to_dict(row, author_name=names.get(row.author_id or 0))

    async def list_mentions(
        self, db: AsyncSession, user_id: int, *, limit: int = 20, unread_only: bool = False
    ) -> list[dict]:
        """@ 到我的评论

        ``mentions`` 是 ``String(500)``：先用 SQL ``like`` 粗筛（``%<uid>%``），再在应用层把每行
        ``mentions`` **解析成整数列表**做精确判断 —— 修 v2 直接 ``contains`` 会误匹配 ``[11,21]`` 的问题。
        ``unread_only=True`` 的语义是「**未解决**」（既有表无独立已读状态，见 ``__init__.py``）。
        """
        cap = min(max(limit * 5, limit), MAX_PAGE_SIZE)
        stmt = select(TeamComment).where(
            TeamComment.mentions.isnot(None),
            TeamComment.mentions.like(f"%{int(user_id)}%"),
        )
        if unread_only:
            stmt = stmt.where(TeamComment.is_resolved.is_(False))
        stmt = stmt.order_by(TeamComment.created_at.desc(), TeamComment.id.desc()).limit(cap)
        rows = (await db.execute(stmt)).scalars().all()

        matched = [row for row in rows if int(user_id) in parse_mentions(row.mentions)][
            : min(limit, MAX_PAGE_SIZE)
        ]
        names = await _author_names(db, {row.author_id for row in matched if row.author_id})
        return [_row_to_dict(row, author_name=names.get(row.author_id or 0)) for row in matched]

    async def statistics(
        self,
        db: AsyncSession,
        *,
        content_type: Optional[str] = None,
        content_id: Optional[int] = None,
    ) -> dict:
        """评论统计（真实聚合，纯函数 ``summarize`` 负责算）"""
        stmt = select(TeamComment.author_id, TeamComment.is_resolved)
        if content_type:
            stmt = stmt.where(TeamComment.content_type == content_type)
        if content_id is not None:
            stmt = stmt.where(TeamComment.content_id == content_id)
        rows = [
            {"author_id": author_id, "is_resolved": bool(resolved)}
            for author_id, resolved in (await db.execute(stmt)).all()
        ]
        return summarize(rows)

    # ------------------------------------------------------------ 写
    async def create(
        self, db: AsyncSession, payload: TeamCommentCreate, *, author_id: int
    ) -> dict:
        """发表评论：校验父评论属于同一内容对象；``text`` 入库前 ``html.escape``"""
        if payload.parent_id is not None:
            parent = await team_comment_crud.get(db, payload.parent_id)
            if parent is None:
                raise BadRequestError("父评论不存在")
            if (parent.content_type, parent.content_id) != (payload.content_type, payload.content_id):
                raise BadRequestError("父评论不属于同一内容对象")

        mentions = dump_mentions(payload.mentions)
        if payload.mentions and mentions is None:
            raise BadRequestError("mentions 无法序列化（请提供正整数用户 ID）")

        now = datetime.now()
        row = await team_comment_crud.create(
            db,
            {
                "content_type": payload.content_type,
                "content_id": payload.content_id,
                "author_id": author_id,
                "parent_id": payload.parent_id,
                "text": html.escape(payload.text),
                "mentions": mentions,
                "is_resolved": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        return _row_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        comment_id: int,
        payload: TeamCommentUpdate,
        *,
        user_id: int,
        is_admin: bool,
    ) -> dict:
        row = await self._ensure(db, comment_id)
        self._assert_can_write(row, user_id=user_id, is_admin=is_admin, action="修改")
        updated = await team_comment_crud.update(
            db, row, {"text": html.escape(payload.text), "updated_at": datetime.now()}
        )
        return _row_to_dict(updated)

    async def delete(
        self, db: AsyncSession, comment_id: int, *, user_id: int, is_admin: bool
    ) -> int:
        """删除评论及其**全部子孙**（递归收集后一条语句删除），返回实际删除条数"""
        row = await self._ensure(db, comment_id)
        self._assert_can_write(row, user_id=user_id, is_admin=is_admin, action="删除")
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
        await team_comment_crud.remove_many(db, to_delete)
        return len(to_delete)

    async def resolve(
        self, db: AsyncSession, comment_id: int, *, user_id: int, is_admin: bool
    ) -> dict:
        """标记已解决：**作者或管理员**才可；已解决则返回 400（不静默重复）"""
        row = await self._ensure(db, comment_id)
        self._assert_can_write(row, user_id=user_id, is_admin=is_admin, action="标记解决")
        if row.is_resolved:
            raise BadRequestError("该评论已是已解决状态")
        now = datetime.now()
        updated = await team_comment_crud.update(
            db,
            row,
            {
                "is_resolved": True,
                "resolved_by": user_id,
                "resolved_at": now,
                "updated_at": now,
            },
        )
        return _row_to_dict(updated)


team_comment_service = TeamCommentService()

__all__ = [
    "MAX_PAGE_SIZE",
    "TeamCommentCRUD",
    "TeamCommentService",
    "build_threads",
    "dump_mentions",
    "parse_mentions",
    "summarize",
    "team_comment_crud",
    "team_comment_service",
]
