"""协作邀请的业务逻辑（T5-11 批次 9）

**与 v2 的差异** —— v2 的 ``collaboration_invites.py`` 是**进程内 dict**：
重启即丢、多 worker 各持一份、邀请 URL 硬编码 ``http://localhost:3000/...``、
且 ``accept`` / 查询 / 撤销**全部没有鉴权**。这里改为：

  - 真表 ``collaboration_invites``（本批次新建，alembic 迁移 ``a7c1e5f9b2d4``）；
  - ``target_type`` 泛化：``article``（文章协作编辑）/ ``workspace``（加入工作区）；
  - 建邀请要**目标归属校验**：article 需作者本人（或管理员），workspace 需 admin 及以上；
  - ``accept`` 需要登录，校验「有效 / 未过期 / 未超次数」，**工作区邀请会真实写入成员关系**；
  - ``require_document_access`` 给 yjs 房间用：作者本人，或持有指向该文档的有效邀请码。
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.collaboration import CollaborationInvite
from src.api.v3.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.content.collaboration.crud import collaboration_invite_crud
from src.api.v3.modules.content.collaboration.schema import (
    INVITE_PERMISSIONS,
    ROLE_LEVELS,
    TARGET_TYPES,
    InviteCreate,
    InviteOut,
)
from src.api.v3.modules.content.collaboration.workspace_service import workspace_service

logger = get_logger("content.collaboration.invite")

#: 邀请权限 → 工作区成员角色的映射
_PERMISSION_TO_ROLE = {"view": "viewer", "edit": "editor"}


def _invite_out(row) -> dict:
    return InviteOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class InviteService:
    """协作邀请"""

    async def _ensure(self, db: AsyncSession, invite_id: int) -> CollaborationInvite:
        row = await collaboration_invite_crud.get(db, invite_id)
        if row is None:
            raise NotFoundError("邀请不存在")
        return row

    async def list_invites(
        self,
        db: AsyncSession,
        *,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        rows, total = await collaboration_invite_crud.list(
            db,
            page=page,
            page_size=page_size,
            filters={"target_type": target_type, "target_id": target_id},
        )
        return [_invite_out(row) for row in rows], total

    async def _assert_target_owner(
        self, db: AsyncSession, target_type: str, target_id: int, creator_id: int, is_admin: bool
    ) -> None:
        if target_type == "article":
            article = await db.get(Article, target_id)
            if article is None:
                raise NotFoundError("文章不存在")
            if getattr(article, "user", None) != creator_id and not is_admin:
                raise ForbiddenError("只有文章作者可以发起协作邀请")
            return
        # workspace：需要 admin 及以上（管理员全局放行）
        await workspace_service.require_level(
            db, target_id, creator_id, 1 if is_admin else ROLE_LEVELS["admin"]
        )

    async def create(
        self, db: AsyncSession, payload: InviteCreate, creator_id: int, *, is_admin: bool = False
    ) -> dict:
        if payload.target_type not in TARGET_TYPES:
            raise BadRequestError(
                f"目标类型不合法: {payload.target_type}（可选 {'/'.join(TARGET_TYPES)}）"
            )
        if payload.permission not in INVITE_PERMISSIONS:
            raise BadRequestError(
                f"权限不合法: {payload.permission}（可选 {'/'.join(INVITE_PERMISSIONS)}）"
            )
        await self._assert_target_owner(
            db, payload.target_type, payload.target_id, creator_id, is_admin
        )
        # 同一目标 + 同一创建人的**旧有效邀请**先作废，避免邀请码堆积（v2 是删内存里的旧项）
        stale, _total = await collaboration_invite_crud.list(
            db,
            page=1,
            page_size=0,  # 0 = 不分页
            filters={
                "target_type": payload.target_type,
                "target_id": payload.target_id,
                "creator_id": creator_id,
                "is_active": True,
            },
        )
        for old in stale:
            await collaboration_invite_crud.update(db, old, {"is_active": False})

        now = datetime.now()
        row = await collaboration_invite_crud.create(
            db,
            {
                "invite_code": secrets.token_urlsafe(24),
                "target_type": payload.target_type,
                "target_id": payload.target_id,
                "permission": payload.permission,
                "creator_id": creator_id,
                "expires_at": now + timedelta(hours=payload.expire_hours),
                "max_uses": payload.max_uses,
                "use_count": 0,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        )
        return _invite_out(row)

    async def get_by_code(self, db: AsyncSession, invite_code: str) -> dict:
        row = await collaboration_invite_crud.get_by(db, invite_code=invite_code)
        if row is None:
            raise NotFoundError("邀请不存在或已失效")
        return _invite_out(row)

    async def get_invite(self, db: AsyncSession, invite_id: int) -> dict:
        """按 ID 取邀请详情（供路由层使用，避免外部直接碰 ``_ensure``）"""
        return _invite_out(await self._ensure(db, invite_id))

    async def revoke(
        self, db: AsyncSession, invite_id: int, user_id: int, *, is_admin: bool = False
    ) -> None:
        row = await self._ensure(db, invite_id)
        if row.creator_id != user_id and not is_admin:
            raise ForbiddenError("只有邀请创建者可以撤销")
        await collaboration_invite_crud.update(
            db, row, {"is_active": False, "updated_at": datetime.now()}
        )

    async def accept(self, db: AsyncSession, invite_code: str, user_id: int) -> dict:
        """接受邀请

        - 工作区邀请：**真实写入** ``workspace_members``（已是成员则不再重复加，只回显）；
        - 文章邀请：v3 没有「文章协作者」表，因此只校验并递增使用次数，
          真正的写权限由 yjs 房间的 ``require_document_access`` 把关。
        """
        row = await collaboration_invite_crud.get_by(db, invite_code=invite_code)
        if row is None or not row.is_active:
            raise NotFoundError("邀请不存在或已失效")
        now = datetime.now()
        if row.expires_at is not None and row.expires_at < now:
            raise BadRequestError("邀请已过期")
        if row.max_uses and (row.use_count or 0) >= row.max_uses:
            raise BadRequestError("邀请使用次数已用尽")

        result: dict = {"invite": _invite_out(row), "target_type": row.target_type}
        if row.target_type == "workspace":
            role = _PERMISSION_TO_ROLE.get(row.permission or "view", "viewer")
            try:
                member = await workspace_service.add_member(
                    db,
                    row.target_id,
                    _member_payload(user_id, role),
                    user_id=row.creator_id or user_id,
                )
                result["member"] = member
            except ConflictError:
                # 已是成员：幂等放行
                result["member"] = None
                result["already_member"] = True
            except ForbiddenError as exc:
                raise BadRequestError(f"无法加入工作区：{exc}") from exc

        updated = await collaboration_invite_crud.update(
            db, row, {"use_count": (row.use_count or 0) + 1, "updated_at": now}
        )
        result["invite"] = _invite_out(updated)
        return result

    async def require_document_access(
        self,
        db: AsyncSession,
        article_id: int,
        user_id: Optional[int],
        invite_code: Optional[str] = None,
    ) -> None:
        """yjs 房间的准入：**作者本人**，或**持有指向该文档的有效邀请码**

        注意这里用 ``raise`` 表达拒绝（WS 端点会先 accept 再关连接，见 ``yjs.py``）。
        """
        if user_id is None:
            raise ForbiddenError("未认证：协同编辑需要登录")
        article = await db.get(Article, article_id)
        if article is None:
            raise NotFoundError("文档不存在")
        if getattr(article, "user", None) == user_id:
            return
        if invite_code:
            row = await collaboration_invite_crud.get_by(db, invite_code=invite_code)
            if (
                row is not None
                and row.is_active
                and row.target_type == "article"
                and row.target_id == article_id
                and (row.expires_at is None or row.expires_at >= datetime.now())
                and (not row.max_uses or (row.use_count or 0) < row.max_uses)
            ):
                return
        raise ForbiddenError("无权进入该文档的协同编辑")


def _member_payload(user_id: int, role: str):
    """延迟 import：``MemberAdd`` 只在 accept 分支用到"""
    from src.api.v3.modules.content.collaboration.schema import MemberAdd

    return MemberAdd(user_id=user_id, role=role)


invite_service = InviteService()
