"""工作区 / 成员 / 任务 的业务逻辑（T5-11 批次 9）

**与 v2 的差异**（v2 的 ``team_collaboration.py`` 只有一半能跑）：

  - v2 的 ``POST /workspaces`` **没有 ``@router`` 装饰器** → 根本建不了工作区；这里补上；
  - v2 的 ``PUT /tasks/{id}/status`` **完全没有权限与归属校验**（任何登录用户可改任意任务）；
    这里统一走 ``_require_level``：改任务需 **editor**，且必须先确认调用方属于该工作区；
  - v2 的错误用 ``ok()/fail()`` 返回 **HTTP 200 + success:false**；这里改成正确的 HTTP 语义
    （403 / 404 / 409 走 v3 的 ``ForbiddenError`` / ``NotFoundError`` / ``ConflictError``）。

角色层级（与 v2 一致）：``viewer(1) < editor(2) < admin(3) < owner(4)``
（``src/api/v3/modules/content/collaboration/schema.py`` 的 ``ROLE_LEVELS``）。
"""

import re
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.collaboration import Task, Workspace, WorkspaceMember
from shared.models.user import User
from src.api.v3.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from src.api.v3.modules.content.collaboration.crud import (
    task_crud,
    workspace_crud,
    workspace_member_crud,
)
from src.api.v3.modules.content.collaboration.schema import (
    MEMBER_ROLES,
    ROLE_LEVELS,
    TASK_PRIORITIES,
    TASK_STATUSES,
    MemberAdd,
    MemberOut,
    MemberRoleUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceUpdate,
)

MAX_PAGE_SIZE = 100


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value.strip().lower())
    return slug.strip("-")[:200] or "workspace"


def _workspace_out(row, *, member_count: int = 0) -> dict:
    data = WorkspaceOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["member_count"] = member_count
    return data


def _member_out(row, *, user: Optional[User] = None) -> dict:
    data = MemberOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    if user is not None:
        data["username"] = user.username
        data["email"] = user.email
    return data


def _task_out(row) -> dict:
    return TaskOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class WorkspaceService:
    """工作区与成员权限"""

    # ------------------------------------------------------------ 权限
    async def require_level(
        self, db: AsyncSession, workspace_id: int, user_id: int, min_level: int
    ) -> WorkspaceMember:
        """调用方必须是该工作区的**活跃成员**且层级不低于 ``min_level``"""
        member = await workspace_member_crud.get_by(
            db, workspace_id=workspace_id, user_id=user_id, is_active=True
        )
        if member is None:
            raise ForbiddenError("你不是该工作区成员")
        level = ROLE_LEVELS.get(member.role or "viewer", 1)
        if level < min_level:
            need = next((name for name, value in ROLE_LEVELS.items() if value == min_level), min_level)
            raise ForbiddenError(f"需要 {need} 及以上权限（当前 {member.role or 'viewer'}）")
        return member

    async def _member_count(self, db: AsyncSession, workspace_id: int) -> int:
        return int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(WorkspaceMember)
                    .where(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.is_active.is_(True),
                    )
                )
            ).scalar()
            or 0
        )

    async def _ensure_workspace(self, db: AsyncSession, workspace_id: int) -> Workspace:
        row = await workspace_crud.get(db, workspace_id)
        if row is None:
            raise NotFoundError("工作区不存在")
        return row

    # ------------------------------------------------------------ 工作区
    async def list_my_workspaces(self, db: AsyncSession, user_id: int) -> list[dict]:
        """我是活跃成员的工作区（含我的角色）"""
        stmt = (
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id, WorkspaceMember.is_active.is_(True))
            .order_by(Workspace.id.desc())
        )
        rows = (await db.execute(stmt)).all()
        result = []
        for workspace, role in rows:
            data = _workspace_out(
                workspace, member_count=await self._member_count(db, workspace.id)
            )
            data["role"] = role
            result.append(data)
        return result

    async def get_by_slug(self, db: AsyncSession, slug: str, user_id: int) -> dict:
        workspace = await workspace_crud.get_by(db, slug=slug)
        if workspace is None:
            raise NotFoundError("工作区不存在")
        member = await self.require_level(db, workspace.id, user_id, ROLE_LEVELS["viewer"])
        data = _workspace_out(workspace, member_count=await self._member_count(db, workspace.id))
        data["role"] = member.role
        return data

    async def get_detail(self, db: AsyncSession, workspace_id: int, user_id: int) -> dict:
        """按 ID 取工作区详情（需 viewer 及以上）"""
        workspace = await self._ensure_workspace(db, workspace_id)
        member = await self.require_level(db, workspace_id, user_id, ROLE_LEVELS["viewer"])
        data = _workspace_out(workspace, member_count=await self._member_count(db, workspace_id))
        data["role"] = member.role
        return data

    async def create(self, db: AsyncSession, payload: WorkspaceCreate, owner_id: int) -> dict:
        slug = payload.slug or _slugify(payload.name)
        if await workspace_crud.exists(db, slug=slug):
            raise ConflictError(f"工作区标识已存在: {slug}")
        now = datetime.now()
        workspace = await workspace_crud.create(
            db,
            {
                "name": payload.name,
                "slug": slug,
                "description": payload.description,
                "owner_id": owner_id,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        )
        # 创建者自动成为 owner 成员（v2 也这么做，但它建不出工作区）
        await workspace_member_crud.create(
            db,
            {
                "workspace_id": workspace.id,
                "user_id": owner_id,
                "role": "owner",
                "joined_at": now,
                "is_active": True,
            },
        )
        return _workspace_out(workspace, member_count=1)

    async def update(
        self, db: AsyncSession, workspace_id: int, payload: WorkspaceUpdate, user_id: int
    ) -> dict:
        await self._ensure_workspace(db, workspace_id)
        await self.require_level(db, workspace_id, user_id, ROLE_LEVELS["admin"])
        updated = await workspace_crud.update(
            db,
            await workspace_crud.get(db, workspace_id),
            payload.model_dump(exclude_unset=True) | {"updated_at": datetime.now()},
        )
        return _workspace_out(updated, member_count=await self._member_count(db, workspace_id))

    async def delete(self, db: AsyncSession, workspace_id: int, user_id: int) -> None:
        workspace = await self._ensure_workspace(db, workspace_id)
        if workspace.owner_id != user_id:
            await self.require_level(db, workspace_id, user_id, ROLE_LEVELS["owner"])
        # 软删：工作区与成员关系一并停用，避免残留可访问路径
        await workspace_crud.update(
            db, workspace, {"is_active": False, "updated_at": datetime.now()}
        )
        for member in (
            await db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.is_active.is_(True),
                )
            )
        ).scalars().all():
            await workspace_member_crud.update(db, member, {"is_active": False})

    # ------------------------------------------------------------ 成员
    async def list_members(self, db: AsyncSession, workspace_id: int, user_id: int) -> list[dict]:
        await self._ensure_workspace(db, workspace_id)
        await self.require_level(db, workspace_id, user_id, ROLE_LEVELS["viewer"])
        stmt = (
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id, isouter=True)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.is_active.is_(True),
            )
            .order_by(WorkspaceMember.id)
        )
        return [_member_out(member, user=user) for member, user in (await db.execute(stmt)).all()]

    async def add_member(
        self, db: AsyncSession, workspace_id: int, payload: MemberAdd, user_id: int
    ) -> dict:
        await self._ensure_workspace(db, workspace_id)
        await self.require_level(db, workspace_id, user_id, ROLE_LEVELS["admin"])
        if payload.role not in MEMBER_ROLES:
            raise BadRequestError(f"角色不合法: {payload.role}（可选 {'/'.join(MEMBER_ROLES)}）")
        if await db.get(User, payload.user_id) is None:
            raise NotFoundError("用户不存在")
        existing = await workspace_member_crud.get_by(
            db, workspace_id=workspace_id, user_id=payload.user_id
        )
        now = datetime.now()
        if existing is not None:
            if existing.is_active:
                raise ConflictError("该用户已是工作区成员")
            # 之前移除过：复活并更新角色
            revived = await workspace_member_crud.update(
                db,
                existing,
                {"role": payload.role, "is_active": True, "joined_at": now},
            )
            return _member_out(revived, user=await db.get(User, payload.user_id))
        member = await workspace_member_crud.create(
            db,
            {
                "workspace_id": workspace_id,
                "user_id": payload.user_id,
                "role": payload.role,
                "joined_at": now,
                "is_active": True,
            },
        )
        return _member_out(member, user=await db.get(User, payload.user_id))

    async def remove_member(
        self, db: AsyncSession, workspace_id: int, member_user_id: int, user_id: int
    ) -> None:
        await self._ensure_workspace(db, workspace_id)
        await self.require_level(db, workspace_id, user_id, ROLE_LEVELS["admin"])
        member = await workspace_member_crud.get_by(
            db, workspace_id=workspace_id, user_id=member_user_id, is_active=True
        )
        if member is None:
            raise NotFoundError("成员不存在")
        if (member.role or "viewer") == "owner":
            raise ForbiddenError("不能移除工作区所有者")
        await workspace_member_crud.update(db, member, {"is_active": False})

    async def update_member_role(
        self,
        db: AsyncSession,
        workspace_id: int,
        member_user_id: int,
        payload: MemberRoleUpdate,
        user_id: int,
    ) -> dict:
        await self._ensure_workspace(db, workspace_id)
        # 改角色需要 owner（与 v2 一致）
        await self.require_level(db, workspace_id, user_id, ROLE_LEVELS["owner"])
        if payload.role not in MEMBER_ROLES:
            raise BadRequestError(f"角色不合法: {payload.role}（可选 {'/'.join(MEMBER_ROLES)}）")
        member = await workspace_member_crud.get_by(
            db, workspace_id=workspace_id, user_id=member_user_id, is_active=True
        )
        if member is None:
            raise NotFoundError("成员不存在")
        updated = await workspace_member_crud.update(db, member, {"role": payload.role})
        return _member_out(updated, user=await db.get(User, member_user_id))


class TaskService:
    """工作区任务"""

    async def _ensure_task(self, db: AsyncSession, task_id: int) -> Task:
        row = await task_crud.get(db, task_id)
        if row is None:
            raise NotFoundError("任务不存在")
        return row

    async def list_tasks(
        self,
        db: AsyncSession,
        workspace_id: int,
        user_id: int,
        *,
        status: Optional[str] = None,
        assigned_to: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        await workspace_service.require_level(
            db, workspace_id, user_id, ROLE_LEVELS["viewer"]
        )
        rows, total = await task_crud.list(
            db,
            page=page,
            page_size=min(page_size, MAX_PAGE_SIZE),
            filters={"workspace_id": workspace_id, "status": status, "assigned_to": assigned_to},
        )
        return [_task_out(row) for row in rows], total

    async def create_task(
        self, db: AsyncSession, workspace_id: int, payload: TaskCreate, user_id: int
    ) -> dict:
        await workspace_service.require_level(
            db, workspace_id, user_id, ROLE_LEVELS["editor"]
        )
        if payload.priority not in TASK_PRIORITIES:
            raise BadRequestError(f"优先级不合法: {payload.priority}")
        now = datetime.now()
        row = await task_crud.create(
            db,
            {
                "workspace_id": workspace_id,
                "title": payload.title,
                "description": payload.description,
                "status": "pending",
                "priority": payload.priority,
                "assigned_to": payload.assigned_to,
                "created_by": user_id,
                "due_date": payload.due_date,
                "created_at": now,
                "updated_at": now,
            },
        )
        return _task_out(row)

    async def update_task(
        self, db: AsyncSession, task_id: int, payload: TaskUpdate, user_id: int
    ) -> dict:
        """改任务：**必须先确认调用方属于该工作区**（v2 这里是越权入口）"""
        row = await self._ensure_task(db, task_id)
        await workspace_service.require_level(
            db, row.workspace_id, user_id, ROLE_LEVELS["editor"]
        )
        data = payload.model_dump(exclude_unset=True)
        if "status" in data:
            if data["status"] not in TASK_STATUSES:
                raise BadRequestError(f"状态不合法: {data['status']}")
            # completed 时补完成时间；回退到其它状态则清空
            data["completed_at"] = datetime.now() if data["status"] == "completed" else None
        if "priority" in data and data["priority"] not in TASK_PRIORITIES:
            raise BadRequestError(f"优先级不合法: {data['priority']}")
        updated = await task_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _task_out(updated)

    async def delete_task(self, db: AsyncSession, task_id: int, user_id: int) -> None:
        row = await self._ensure_task(db, task_id)
        await workspace_service.require_level(
            db, row.workspace_id, user_id, ROLE_LEVELS["admin"]
        )
        await task_crud.remove(db, row)


workspace_service = WorkspaceService()
task_service = TaskService()
