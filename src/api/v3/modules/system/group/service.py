"""group 模块业务逻辑

要点：

  - 组成员数用**一次 group by** 取回，避免列表页 N+1
  - 组树与环路防护（``parent_id`` 不能是自己或自己的后代）
  - 删除组前检查子组与成员，避免产生孤儿数据
  - **任何变更后都失效数据范围缓存**（``invalidate_scope_cache``）——
    这是审计里 P1-1 那类"改了权限但不生效"问题的正解
"""

from typing import Dict, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.rbac.permission_group import PermissionGroup
from shared.models.rbac.role_group import RoleGroup
from shared.models.rbac.user_group_member import UserGroupMember
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.scope import invalidate_scope_cache
from src.api.v3.modules.system.group.crud import (
    permission_group_crud,
)
from src.api.v3.modules.system.group.schema import (
    PermissionGroupCreate,
    PermissionGroupUpdate,
)

logger = get_logger("group")


def _group_out(group: PermissionGroup, *, member_count: int = 0) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "code": group.code,
        "description": group.description,
        "parent_id": group.parent_id,
        "sort_order": group.sort_order or 0,
        "owner_id": group.owner_id,
        "is_active": bool(group.is_active),
        "created_at": group.created_at,
        "updated_at": group.updated_at,
        "member_count": member_count,
        "children": [],
    }


def build_tree(groups: Sequence[dict]) -> List[dict]:
    by_id = {item["id"]: item for item in groups}
    roots: List[dict] = []
    for item in by_id.values():
        parent = by_id.get(item["parent_id"]) if item["parent_id"] else None
        if parent is not None and parent["id"] != item["id"]:
            parent["children"].append(item)
        else:
            roots.append(item)

    def _sort(nodes: List[dict]) -> List[dict]:
        nodes.sort(key=lambda node: (node.get("sort_order") or 0, node["id"]))
        for node in nodes:
            _sort(node["children"])
        return nodes

    return _sort(roots)


class GroupService:
    """权限用户组管理"""

    # ------------------------------------------------------------------ 内部
    @staticmethod
    async def _member_counts(db: AsyncSession, group_ids: Sequence[int]) -> Dict[int, int]:
        if not group_ids:
            return {}
        stmt = (
            select(UserGroupMember.group_id, func.count())
            .where(UserGroupMember.group_id.in_(list(group_ids)))
            .group_by(UserGroupMember.group_id)
        )
        return {int(group_id): int(count or 0) for group_id, count in (await db.execute(stmt)).all()}

    async def list_groups(
        self,
        db: AsyncSession,
        *,
        is_active: Optional[bool] = None,
        keyword: Optional[str] = None,
    ) -> List[dict]:
        groups, _total = await permission_group_crud.list(
            db,
            page=1,
            page_size=0,
            keyword=keyword,
            filters={"is_active": is_active},
            order_by="sort_order",
            order="asc",
        )
        counts = await self._member_counts(db, [group.id for group in groups])
        return [_group_out(group, member_count=counts.get(group.id, 0)) for group in groups]

    async def tree(self, db: AsyncSession, *, is_active: Optional[bool] = None) -> List[dict]:
        return build_tree(await self.list_groups(db, is_active=is_active))

    async def get_group(self, db: AsyncSession, group_id: int) -> PermissionGroup:
        group = await permission_group_crud.get(db, group_id)
        if group is None:
            raise NotFoundError("权限组不存在")
        return group

    async def get_group_out(self, db: AsyncSession, group_id: int) -> dict:
        group = await self.get_group(db, group_id)
        counts = await self._member_counts(db, [group.id])
        return _group_out(group, member_count=counts.get(group.id, 0))

    async def create_group(self, db: AsyncSession, payload: PermissionGroupCreate) -> dict:
        if await permission_group_crud.exists(db, code=payload.code):
            raise ConflictError(f"权限组标识 {payload.code} 已存在")
        if payload.parent_id is not None:
            await self.get_group(db, payload.parent_id)

        group = await permission_group_crud.create(db, payload.model_dump(exclude_unset=True))
        await invalidate_scope_cache()
        return _group_out(group)

    async def update_group(
        self, db: AsyncSession, group_id: int, payload: PermissionGroupUpdate
    ) -> dict:
        group = await self.get_group(db, group_id)
        data = payload.model_dump(exclude_unset=True)

        if data.get("parent_id") == group_id:
            raise BadRequestError("父组不能是自己")
        if "code" in data and data["code"]:
            existing = await permission_group_crud.get_by(db, code=data["code"])
            if existing is not None and existing.id != group_id:
                raise ConflictError(f"权限组标识 {data['code']} 已存在")
        if data.get("parent_id") is not None:
            await self._assert_no_cycle(db, group_id, data["parent_id"])

        group = await permission_group_crud.update(db, group, data)
        await invalidate_scope_cache()
        return await self.get_group_out(db, group.id)

    async def _assert_no_cycle(self, db: AsyncSession, group_id: int, parent_id: int) -> None:
        """防止把组挂到自己的后代下形成环（与 category 同一策略）"""
        current = parent_id
        for _ in range(64):
            if current == group_id:
                raise BadRequestError("父组不能是自身或其子组")
            parent = await permission_group_crud.get(db, current)
            if parent is None or parent.parent_id is None:
                return
            current = parent.parent_id
        raise BadRequestError("组层级过深，疑似存在循环引用")

    async def delete_group(self, db: AsyncSession, group_id: int) -> None:
        group = await self.get_group(db, group_id)

        child_count = await permission_group_crud.count(db, parent_id=group_id)
        if child_count:
            raise ConflictError(f"存在 {child_count} 个子组，请先处理")

        counts = await self._member_counts(db, [group_id])
        member_count = counts.get(group_id, 0)
        if member_count:
            raise ConflictError(f"组内仍有 {member_count} 名成员，请先移出")

        # 角色绑定可以安全清理（它只是"自定义范围"的配置）
        await db.execute(RoleGroup.__table__.delete().where(RoleGroup.group_id == group_id))
        await db.commit()

        await permission_group_crud.remove(db, group)
        await invalidate_scope_cache()

    # ------------------------------------------------------------------ 成员
    async def list_members(self, db: AsyncSession, group_id: int) -> List[dict]:
        await self.get_group(db, group_id)
        stmt = (
            select(User)
            .join(UserGroupMember, UserGroupMember.user_id == User.id)
            .where(UserGroupMember.group_id == group_id)
            .order_by(User.id.asc())
        )
        return [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": bool(user.is_active),
            }
            for user in (await db.execute(stmt)).scalars().all()
        ]

    async def set_members(
        self, db: AsyncSession, group_id: int, user_ids: Sequence[int]
    ) -> List[dict]:
        """全量覆盖组成员（差量增删，避免整表重写）"""
        await self.get_group(db, group_id)
        target = {int(uid) for uid in user_ids}

        current_rows = await db.execute(
            select(UserGroupMember.user_id).where(UserGroupMember.group_id == group_id)
        )
        current = {int(uid) for uid in current_rows.scalars().all() if uid is not None}

        for user_id in target - current:
            db.add(UserGroupMember(user_id=user_id, group_id=group_id))
        for user_id in current - target:
            await db.execute(
                UserGroupMember.__table__.delete().where(
                    UserGroupMember.group_id == group_id,
                    UserGroupMember.user_id == user_id,
                )
            )
        await db.commit()

        # 成员变化直接影响"可访问的用户集合"
        await invalidate_scope_cache()
        return await self.list_members(db, group_id)

    async def remove_member(self, db: AsyncSession, group_id: int, user_id: int) -> None:
        await self.get_group(db, group_id)
        await db.execute(
            UserGroupMember.__table__.delete().where(
                UserGroupMember.group_id == group_id,
                UserGroupMember.user_id == user_id,
            )
        )
        await db.commit()
        await invalidate_scope_cache()

    # ------------------------------------------------------------------ 角色绑定
    async def list_roles(self, db: AsyncSession, group_id: int) -> List[dict]:
        from shared.models.rbac.role import Role

        await self.get_group(db, group_id)
        stmt = (
            select(Role)
            .join(RoleGroup, RoleGroup.role_id == Role.id)
            .where(RoleGroup.group_id == group_id)
            .order_by(Role.id.asc())
        )
        return [
            {
                "id": role.id,
                "name": role.name,
                "slug": role.slug,
                "data_scope": role.data_scope,
            }
            for role in (await db.execute(stmt)).scalars().all()
        ]

    async def set_roles(
        self, db: AsyncSession, group_id: int, role_ids: Sequence[int]
    ) -> List[dict]:
        """全量覆盖"绑定到该组的角色"（配合 ``roles.data_scope=5`` 使用）"""
        await self.get_group(db, group_id)
        target = {int(rid) for rid in role_ids}

        if target:
            from shared.models.rbac.role import Role

            found = (
                await db.execute(select(Role.id).where(Role.id.in_(sorted(target))))
            ).scalars().all()
            missing = target - {int(rid) for rid in found}
            if missing:
                raise BadRequestError(f"角色不存在: {', '.join(str(m) for m in sorted(missing))}")

        current_rows = await db.execute(
            select(RoleGroup.role_id).where(RoleGroup.group_id == group_id)
        )
        current = {int(rid) for rid in current_rows.scalars().all() if rid is not None}

        for role_id in target - current:
            db.add(RoleGroup(role_id=role_id, group_id=group_id))
        for role_id in current - target:
            await db.execute(
                RoleGroup.__table__.delete().where(
                    RoleGroup.group_id == group_id, RoleGroup.role_id == role_id
                )
            )
        await db.commit()

        await invalidate_scope_cache()
        return await self.list_roles(db, group_id)


group_service = GroupService()
