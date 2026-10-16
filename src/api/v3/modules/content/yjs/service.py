"""yjs 协同文档模块业务逻辑：快照落库 / 版本历史 / 回滚 / 协作者 / 房间视图

源能力来自 v2 的 ``shared/services/chat/yjs_collaboration.py``（Yjs CRDT 协同编辑）。
**逐项对照** —— 哪些能真实落地、哪些必须如实降级：

| v2 的做法 | 问题 | 本模块 / v3 |
|---|---|---|
| ``YjsCollaborationService.documents`` 是**进程内 dict**，文档内容只存 ``doc.state``（"最后一帧"字节） | 重启即失、多 worker 各持一份；``update_state`` 只做 ``self.state = update``，没有 CRDT 合并，标准 yjs 客户端无法完成初始同步 | 那份二进制**不落库**：真 CRDT 房间 + Redis 跨进程状态由同域 ``content/collaboration/yjs_service.py``（pycrdt 真合并）提供。本模块**不实现第二套房间注册表**——两套注册表会让同一文档的房间状态分裂 |
| ``save_to_database`` 写 ``article_content`` + ``article_revisions``，但 ``content=doc.html_snapshot[:500]`` | 修订正文被**截断到 500 字符**，"版本快照"无法用于恢复 | 正文**完整**入库（``article_revisions.content`` 是 Text 列），并写 ``hash_code`` 供变更检测 |
| 版本只**写**不**读**：没有任何"历史 / 回滚"入口 | 记了修订也用不上 | 新增 ``GET .../versions``（分页）、``GET .../version/{n}``、``POST .../version/{n}/restore``，全部走真表 ``article_revisions`` |
| 每次保存都无条件新建一条修订 | 前端每 30s 自动保存会把表刷满内容相同的行 | ``POST .../snapshot`` 用 ``content_hash``（sha256）去重并返回 ``diff_summary``；``force=true`` 可强制 |
| 权限：v2 的 service **完全没有**鉴权（拿到 document_id 就能读写） | 越权；且 v2 的 WS 端点鉴权失败也放行（匿名） | 读准入复用 ``invite_service.require_document_access``（作者本人，或持指向该文档的有效邀请码）；写准入**额外**要求 ``permission='edit'`` |
| "成员"只存在于内存（``clients`` = 连接） | 重启即丢，且不含"谁被授权" | 协作者来自真表 ``collaboration_invites``（``target_type='article'``）——**持久化**的授权记录 |

**仍是进程内运行时状态**（附理由）：

  - **房间连接表**：``room_registry``（``content/collaboration``）里的 ``clients`` 是 WebSocket
    连接，WS 连接**天然**属于某个进程，无法也不该落库；本模块只做**只读**快照视图。
  - 该注册表**只记录连接数，不记录用户身份**（既有实现的既定事实，本模块不改动它），
    因此"在线用户"如实降级为"在线连接数 + 房间状态（empty/active/crowded）"。

**管理员不自动获得他人协同文档的正文访问权**：协作文档是私密资产，访问权由作者发出的协作
邀请（``collaboration_invites``）授予。后台权限码 ``module_content:collaboration:*``
只决定"能不能调用这些管理端点"，不决定"能不能看某人未公开的草稿"。这条与
``invite_service.require_document_access`` 的既有口径一致。

**纯函数与 DB 操作分离**：``content_hash`` / ``html_stats`` / ``next_revision_number`` /
``content_changed`` / ``room_state`` / ``pick_room`` / ``invite_is_usable`` / ``diff_summary``
一律不碰 DB、不依赖时钟（``now`` 由调用方传入），见 ``_pending_test_yjs.py``。
"""

import hashlib
from datetime import datetime
from typing import Any, Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.article.article_revision import ArticleRevision
from shared.models.collaboration import CollaborationInvite
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.content.collaboration.crud import collaboration_invite_crud
from src.api.v3.modules.content.collaboration.invite_service import invite_service
from src.api.v3.modules.content.collaboration.yjs_service import room_registry
from src.api.v3.modules.content.yjs.schema import (
    ARTICLE_TARGET,
    CROWDED_ROOM_CLIENTS,
    DEFAULT_RESTORE_SUMMARY,
    DEFAULT_SNAPSHOT_SUMMARY,
    MAX_CONTENT_CHARS,
    AuthorOut,
    CollaboratorsOut,
    DocumentAccessOut,
    InviteCollaboratorOut,
    RestoreRequest,
    RestoreResultOut,
    RevisionDetailOut,
    RevisionOut,
    RoomDetailOut,
    RoomOut,
    SnapshotRequest,
    SnapshotResultOut,
)

logger = get_logger("content.yjs")

#: 分页上限
MAX_PAGE_SIZE = 100

#: ``GET /rooms`` 的**口径说明**（如实告知：进程内、无用户身份、跨 worker 状态在 Redis）
ROOM_SCOPE_NOTE = (
    "仅本进程：WebSocket 连接天然属于某个进程，跨 worker 的房间状态在 Redis 中"
    "（content/collaboration 的 yjs_service）；该注册表只记录连接数，不记录用户身份"
)


# ================================================================== 纯函数（无 DB / 无时钟依赖）
def content_hash(html: str) -> str:
    """正文的 sha256 十六进制摘要（**纯函数**）

    写入 ``article_revisions.hash_code``（该列本就存在，v2 从未写过），用于判断"前端上报的
    正文是否真的变了"，避免自动保存堆出内容完全相同的修订。
    """
    return hashlib.sha256((html or "").encode("utf-8")).hexdigest()


def html_stats(html: str) -> dict:
    """正文规模统计（**纯函数**）：字符数 / 行数 / 是否为空 / 是否含 HTML 标签 / 是否超上限"""
    text = html or ""
    return {
        "chars": len(text),
        "lines": text.count("\n") + (1 if text else 0),
        "is_empty": not text.strip(),
        "has_markup": ("<" in text and ">" in text),
        "exceeds_limit": len(text) > MAX_CONTENT_CHARS,
    }


def next_revision_number(existing: Iterable[Any]) -> int:
    """由已有版本号算出下一个版本号（**纯函数**）

    非整数 / ``None`` / 布尔一律忽略（Python 里 ``True`` 也是 ``int``，不拦会算成 ``2``）；
    空集合或全非法值返回 ``1``。
    """
    numbers = [
        int(value)
        for value in existing
        if isinstance(value, int) and not isinstance(value, bool)
    ]
    return (max(numbers) + 1) if numbers else 1


def content_changed(
    previous_hash: Optional[str], previous_content: Optional[str], html: str
) -> bool:
    """正文是否发生变化（**纯函数**）

    优先用 ``hash_code`` 比较（省去逐字比对长正文）；``hash_code`` 缺失时（v2 与
    ``collaboration`` 早期写入的修订都没有这一列）回退到逐字比较；没有历史修订时恒为 ``True``。
    """
    if previous_hash:
        return content_hash(html) != str(previous_hash)
    if previous_content is None:
        return True
    return previous_content != html


def room_state(clients: Any) -> str:
    """房间状态（**纯函数**）：``empty`` / ``active`` / ``crowded``

    非整数（含布尔）一律按 0 处理；``> CROWDED_ROOM_CLIENTS`` 才算 ``crowded``。
    """
    count = clients if isinstance(clients, int) and not isinstance(clients, bool) else 0
    if count <= 0:
        return "empty"
    return "crowded" if count > CROWDED_ROOM_CLIENTS else "active"


def pick_room(rooms: Iterable[Any], document_id: int) -> Optional[dict]:
    """从本进程房间快照里挑出指定文档（**纯函数**）；不存在返回 ``None``"""
    for room in rooms or []:
        if isinstance(room, dict) and room.get("document_id") == document_id:
            return room
    return None


def invite_is_usable(invite: Any, *, now: datetime) -> bool:
    """一条协作邀请当前是否可用（**纯函数**，``now`` 由调用方传入以免依赖时钟）

    判据与 ``invite_service.accept`` / ``require_document_access`` 一致：
    激活 + 未过期 + 未超使用次数。
    """
    if invite is None or not bool(getattr(invite, "is_active", False)):
        return False
    expires_at = getattr(invite, "expires_at", None)
    if expires_at is not None and expires_at < now:
        return False
    max_uses = int(getattr(invite, "max_uses", 0) or 0)
    use_count = int(getattr(invite, "use_count", 0) or 0)
    return not (max_uses and use_count >= max_uses)


def diff_summary(previous: Optional[str], current: str) -> dict:
    """前后两版正文的变更摘要（**纯函数**）：字符增量 / 是否新建 / 是否清空 / 是否相同"""
    before = previous or ""
    after = current or ""
    return {
        "chars_before": len(before),
        "chars_after": len(after),
        "chars_delta": len(after) - len(before),
        "created": not before and bool(after),
        "cleared": bool(before) and not after,
        "is_same": before == after,
    }


# ================================================================== 只读视图构造（行 → dict）
def _revision_out(row: ArticleRevision, *, author_name: Optional[str] = None) -> dict:
    return RevisionOut(
        id=row.id,
        article_id=row.article_id,
        revision_number=row.revision_number,
        title=row.title,
        author_id=row.author_id,
        author_name=author_name,
        change_summary=row.change_summary,
        hash_code=row.hash_code,
        content_chars=len(row.content or ""),
        created_at=row.created_at,
    ).model_dump(mode="json")


# ================================================================== 服务（DB 读写）
class YjsDocumentService:
    """协同文档的持久化面与访问面（实时通道见 ``content/collaboration`` 的 WS 端点）"""

    # -------------------------------------------------------------- 内部：行 / 权限
    async def _ensure_article(self, db: AsyncSession, article_id: int) -> Article:
        """协同文档 = 文章；不存在 → 404"""
        article = await db.get(Article, article_id)
        if article is None:
            raise NotFoundError("协同文档不存在（文章未找到）")
        return article

    async def _content_row(
        self, db: AsyncSession, article_id: int
    ) -> Optional[ArticleContent]:
        """当前正文行（``article_content`` 允许一篇文章多行多语言，这里取最小 id 那行）"""
        return (
            (
                await db.execute(
                    select(ArticleContent)
                    .where(ArticleContent.article == article_id)
                    .order_by(ArticleContent.id.asc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )

    async def _latest_revision(
        self, db: AsyncSession, article_id: int
    ) -> Optional[ArticleRevision]:
        """最近写入的一条修订（按自增 id 倒序，比 revision_number 更能代表"最后写入"）"""
        return (
            (
                await db.execute(
                    select(ArticleRevision)
                    .where(ArticleRevision.article_id == article_id)
                    .order_by(ArticleRevision.id.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )

    async def _revision_by_number(
        self, db: AsyncSession, article_id: int, revision_number: int
    ) -> Optional[ArticleRevision]:
        return (
            (
                await db.execute(
                    select(ArticleRevision)
                    .where(
                        ArticleRevision.article_id == article_id,
                        ArticleRevision.revision_number == revision_number,
                    )
                    .order_by(ArticleRevision.id.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )

    async def _max_revision_number(
        self, db: AsyncSession, article_id: int
    ) -> Optional[int]:
        return (
            await db.execute(
                select(func.max(ArticleRevision.revision_number)).where(
                    ArticleRevision.article_id == article_id
                )
            )
        ).scalar()

    async def _author_names(
        self, db: AsyncSession, user_ids: Iterable[Any]
    ) -> dict[int, str]:
        clean = {int(uid) for uid in user_ids if isinstance(uid, int)}
        if not clean:
            return {}
        rows = (
            await db.execute(select(User.id, User.username).where(User.id.in_(clean)))
        ).all()
        return {int(uid): name for uid, name in rows}

    async def _invite_for(
        self, db: AsyncSession, article_id: int, invite_code: Optional[str]
    ) -> Optional[CollaborationInvite]:
        """按邀请码取一条**仍可用**且指向该文档的邀请；不可用 / 不匹配 → ``None``"""
        if not invite_code:
            return None
        row = await collaboration_invite_crud.get_by(db, invite_code=invite_code)
        if row is None or row.target_type != ARTICLE_TARGET or row.target_id != article_id:
            return None
        return row if invite_is_usable(row, now=datetime.now()) else None

    @staticmethod
    async def require_access(
        db: AsyncSession,
        article_id: int,
        user_id: Optional[int],
        invite_code: Optional[str] = None,
    ) -> None:
        """**读准入**：作者本人，或持指向该文档的有效邀请码（复用 collaboration 的判定）

        拒绝时抛 ``ForbiddenError``（403）、文档不存在抛 ``NotFoundError``（404）。
        """
        await invite_service.require_document_access(db, article_id, user_id, invite_code)

    async def _require_edit(
        self,
        db: AsyncSession,
        article_id: int,
        user_id: Optional[int],
        invite_code: Optional[str] = None,
    ) -> Article:
        """**写准入**：作者本人，或持 ``permission='edit'`` 的有效邀请码

        ``invite_service.require_document_access`` 只判定"能进文档"、不看 ``permission``，
        因此协同**写入**在这里额外收紧（``view`` 邀请码不能改正文）——修 v2「任何登录用户
        都能往任意文档写」的越权面。管理员也**不**自动获得他人草稿的写权限（见模块 docstring）。
        """
        article = await db.get(Article, article_id)
        if article is None:
            raise NotFoundError("协同文档不存在（文章未找到）")
        if user_id is not None and article.user == user_id:
            return article
        # 非作者：先走通用准入（作者 / 有效邀请码），失败即 403
        await invite_service.require_document_access(db, article_id, user_id, invite_code)
        if not invite_code:
            # 逻辑上不可达（上面已放行），保留为防御：没有邀请码就不可能不是作者
            raise ForbiddenError("协同写入需要作者身份或 edit 权限的协作邀请码")
        row = await collaboration_invite_crud.get_by(db, invite_code=invite_code)
        if row is None or (row.permission or "view") != "edit":
            raise ForbiddenError("该邀请码只授予查看权限，协同写入需要 edit 权限")
        return article

    # -------------------------------------------------------------- 房间（进程内只读视图）
    async def rooms(self) -> dict:
        """本进程的活跃协同房间（**运行时状态**，只有连接数，无用户身份）"""
        items: list[dict] = []
        for room in room_registry.snapshot():
            if not isinstance(room, dict):
                continue
            clients = room.get("clients", 0)
            items.append(
                RoomOut(
                    document_id=int(room.get("document_id", 0) or 0),
                    clients=int(clients or 0),
                    state=room_state(clients),
                    active=int(clients or 0) > 0,
                ).model_dump(mode="json")
            )
        return {"rooms": items, "count": len(items), "scope": ROOM_SCOPE_NOTE}

    async def room_detail(
        self,
        db: AsyncSession,
        document_id: int,
        user_id: int,
        *,
        invite_code: Optional[str] = None,
    ) -> dict:
        """单房间详情：连接数（进程内）+ 该文档的真实版本统计（真表）"""
        await self.require_access(db, document_id, user_id, invite_code)
        room = pick_room(room_registry.snapshot(), document_id)
        clients = int((room or {}).get("clients", 0) or 0)
        revision_count = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(ArticleRevision)
                    .where(ArticleRevision.article_id == document_id)
                )
            ).scalar()
            or 0
        )
        latest = await self._latest_revision(db, document_id)
        content_row = await self._content_row(db, document_id)
        content = (content_row.content if content_row is not None else None) or ""
        return RoomDetailOut(
            document_id=document_id,
            clients=clients,
            state=room_state(clients),
            active=clients > 0,
            revision_count=revision_count,
            latest_revision_number=latest.revision_number if latest is not None else None,
            latest_revision_at=latest.created_at if latest is not None else None,
            content_chars=len(content),
            has_content=bool(content),
        ).model_dump(mode="json")

    # -------------------------------------------------------------- 访问权 / 协作者
    async def access(
        self,
        db: AsyncSession,
        article_id: int,
        user_id: Optional[int],
        *,
        invite_code: Optional[str] = None,
    ) -> dict:
        """我在该文档上的访问权（**结构化返回，不抛 403**，便于前端给出准确提示）

        文档不存在 → ``NotFoundError``；否则给出 ``allowed`` / ``can_edit`` 与判定依据。
        """
        article = await self._ensure_article(db, article_id)
        is_author = user_id is not None and article.user == user_id
        invite = None if is_author else await self._invite_for(db, article_id, invite_code)
        if is_author:
            via, permission, reason = "author", "edit", "文档作者"
        elif invite is not None:
            permission = invite.permission or "view"
            via, reason = "invite", f"持有效协作邀请（{permission}）"
        else:
            via, permission, reason = (
                None,
                None,
                "既不是作者，也没有指向该文档的有效协作邀请码",
            )
        can_edit = via == "author" or (via == "invite" and permission == "edit")
        return DocumentAccessOut(
            document_id=article_id,
            title=article.title,
            author_id=article.user,
            is_author=is_author,
            allowed=via is not None,
            can_edit=can_edit,
            via=via,
            permission=permission,
            reason=reason,
        ).model_dump(mode="json")

    async def collaborators(
        self,
        db: AsyncSession,
        article_id: int,
        user_id: int,
        *,
        invite_code: Optional[str] = None,
    ) -> dict:
        """文档协作者来源：作者 + 仍有效的协作邀请（真表 ``collaboration_invites``）

        需先通过读准入。``invite_code`` 只对**作者**回显（拿到码就能进文档）。
        """
        await self.require_access(db, article_id, user_id, invite_code)
        article = await self._ensure_article(db, article_id)
        author = await db.get(User, article.user) if article.user else None
        rows = (
            (
                await db.execute(
                    select(CollaborationInvite)
                    .where(
                        CollaborationInvite.target_type == ARTICLE_TARGET,
                        CollaborationInvite.target_id == article_id,
                        CollaborationInvite.is_active.is_(True),
                    )
                    .order_by(CollaborationInvite.id.desc())
                )
            )
            .scalars()
            .all()
        )
        now = datetime.now()
        show_code = user_id is not None and article.user == user_id
        invites = [
            InviteCollaboratorOut(
                invite_id=row.id,
                invite_code=row.invite_code if show_code else None,
                permission=row.permission,
                creator_id=row.creator_id,
                expires_at=row.expires_at,
                max_uses=int(row.max_uses or 0),
                use_count=int(row.use_count or 0),
                usable=invite_is_usable(row, now=now),
                can_edit=(row.permission or "view") == "edit",
            ).model_dump(mode="json")
            for row in rows
        ]
        author_out = (
            AuthorOut(
                user_id=article.user,
                username=getattr(author, "username", None),
            )
            if article.user
            else None
        )
        return CollaboratorsOut(
            document_id=article_id,
            author=author_out,
            invites=invites,
            invite_count=len(invites),
        ).model_dump(mode="json")

    # -------------------------------------------------------------- 版本历史
    async def versions(
        self,
        db: AsyncSession,
        article_id: int,
        user_id: int,
        *,
        invite_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """版本历史分页（真表 ``article_revisions``，不含正文）"""
        await self.require_access(db, article_id, user_id, invite_code)
        cap = max(1, min(page_size, MAX_PAGE_SIZE))
        total = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(ArticleRevision)
                    .where(ArticleRevision.article_id == article_id)
                )
            ).scalar()
            or 0
        )
        rows = (
            (
                await db.execute(
                    select(ArticleRevision)
                    .where(ArticleRevision.article_id == article_id)
                    .order_by(
                        ArticleRevision.revision_number.desc(),
                        ArticleRevision.id.desc(),
                    )
                    .offset(max(page - 1, 0) * cap)
                    .limit(cap)
                )
            )
            .scalars()
            .all()
        )
        names = await self._author_names(db, (row.author_id for row in rows))
        return [
            _revision_out(row, author_name=names.get(row.author_id or 0)) for row in rows
        ], total

    async def version_detail(
        self,
        db: AsyncSession,
        article_id: int,
        revision_number: int,
        user_id: int,
        *,
        invite_code: Optional[str] = None,
    ) -> dict:
        """单个版本详情（含正文；超过 ``MAX_CONTENT_CHARS`` 时截断返回并标记）"""
        await self.require_access(db, article_id, user_id, invite_code)
        row = await self._revision_by_number(db, article_id, revision_number)
        if row is None:
            raise NotFoundError(f"版本 {revision_number} 不存在")
        author = await db.get(User, row.author_id) if row.author_id else None
        content = row.content or ""
        truncated = len(content) > MAX_CONTENT_CHARS
        return RevisionDetailOut(
            id=row.id,
            article_id=row.article_id,
            revision_number=row.revision_number,
            title=row.title,
            author_id=row.author_id,
            author_name=getattr(author, "username", None),
            change_summary=row.change_summary,
            hash_code=row.hash_code,
            content_chars=len(content),
            created_at=row.created_at,
            content=content[:MAX_CONTENT_CHARS] if truncated else content,
            content_is_truncated=truncated,
            stats=html_stats(content),
        ).model_dump(mode="json")

    # -------------------------------------------------------------- 写：快照 / 回滚
    async def snapshot(
        self,
        db: AsyncSession,
        article_id: int,
        payload: SnapshotRequest,
        user_id: int,
        *,
        invite_code: Optional[str] = None,
    ) -> dict:
        """保存前端上报的正文快照：更新 ``article_content`` + **追加**一条 ``article_revisions``

        - 正文与最新修订一致（按 ``hash_code`` 判定）且未 ``force`` 时**跳过写入**，
          返回 ``saved=False``（不是错误）——避免自动保存把修订表刷满；
        - 同一事务内落正文与修订，不会出现"正文更新了但版本没记"的中间态。
        """
        await self._require_edit(db, article_id, user_id, invite_code)
        html = payload.html
        stats = html_stats(html)
        if stats["exceeds_limit"]:
            raise BadRequestError(
                f"正文过长（{stats['chars']} 字符，上限 {MAX_CONTENT_CHARS}）"
            )
        digest = content_hash(html)
        previous = await self._latest_revision(db, article_id)
        previous_content = previous.content if previous is not None else None
        if not payload.force and not content_changed(
            previous.hash_code if previous is not None else None,
            previous_content,
            html,
        ):
            return SnapshotResultOut(
                document_id=article_id,
                saved=False,
                revision_number=previous.revision_number if previous is not None else None,
                content_hash=digest,
                change=diff_summary(previous_content, html),
                reason="正文与最新修订一致，未新建版本（force=true 可强制）",
            ).model_dump(mode="json")

        now = datetime.now()
        content_row = await self._content_row(db, article_id)
        if content_row is None:
            db.add(
                ArticleContent(
                    article=article_id,
                    content=html,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            content_row.content = html
            content_row.updated_at = now

        number = next_revision_number([await self._max_revision_number(db, article_id)])
        db.add(
            ArticleRevision(
                article_id=article_id,
                revision_number=number,
                author_id=user_id,
                content=html,
                change_summary=(payload.change_summary or DEFAULT_SNAPSHOT_SUMMARY)[:500],
                hash_code=digest,
                created_at=now,
            )
        )
        await db.commit()
        logger.info(
            "协同快照已保存: document=%s revision=%s chars=%s user=%s",
            article_id,
            number,
            stats["chars"],
            user_id,
        )
        return SnapshotResultOut(
            document_id=article_id,
            saved=True,
            revision_number=number,
            content_hash=digest,
            change=diff_summary(previous_content, html),
            reason="已保存并新建修订",
        ).model_dump(mode="json")

    async def restore(
        self,
        db: AsyncSession,
        article_id: int,
        revision_number: int,
        payload: RestoreRequest,
        user_id: int,
        *,
        invite_code: Optional[str] = None,
    ) -> dict:
        """回滚到某历史版本：把该版本正文写回 ``article_content``，并**追加**一条新修订

        历史本身**不重写**（``article_revisions`` 追加式）：回滚之后旧的版本仍可再回滚回来。
        """
        await self._require_edit(db, article_id, user_id, invite_code)
        source = await self._revision_by_number(db, article_id, revision_number)
        if source is None:
            raise NotFoundError(f"版本 {revision_number} 不存在")
        content = source.content or ""
        now = datetime.now()
        content_row = await self._content_row(db, article_id)
        if content_row is None:
            db.add(
                ArticleContent(
                    article=article_id,
                    content=content,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            content_row.content = content
            content_row.updated_at = now

        new_number = next_revision_number([await self._max_revision_number(db, article_id)])
        summary = payload.change_summary or DEFAULT_RESTORE_SUMMARY.format(
            number=revision_number
        )
        db.add(
            ArticleRevision(
                article_id=article_id,
                revision_number=new_number,
                author_id=user_id,
                content=content,
                change_summary=summary[:500],
                hash_code=content_hash(content),
                created_at=now,
            )
        )
        await db.commit()
        logger.info(
            "协同文档回滚: document=%s from=%s new_revision=%s user=%s",
            article_id,
            revision_number,
            new_number,
            user_id,
        )
        return RestoreResultOut(
            document_id=article_id,
            restored_from=revision_number,
            new_revision_number=new_number,
            content_hash=content_hash(content),
        ).model_dump(mode="json")


#: 模块级单例（与其它 v3 模块一致）
yjs_document_service = YjsDocumentService()
