"""role 模块业务逻辑

角色-权限码关联直接操作 ``role_capabilities`` 中间表（与 ``scripts/seed_rbac.py:246-270``
一致），避免在异步会话中触发 relationship 的懒加载。
"""

from typing import List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.rbac.capability import Capability
from shared.models.rbac.role import Role
from shared.models.rbac.role_capability import RoleCapability
from shared.models.rbac.user_role import UserRole
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.invalidate import invalidate_all
from src.api.v3.modules.system.role.crud import role_crud
from src.api.v3.modules.system.role.schema import RoleCreate, RoleUpdate

logger = get_logger("role")


class RoleService:
    """角色管理"""

    async def _count_capabilities(self, db: AsyncSession, role_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(RoleCapability)
            .where(RoleCapability.role_id == role_id)
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def _count_users(self, db: AsyncSession, role_id: int) -> int:
        stmt = select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
        return int((await db.execute(stmt)).scalar() or 0)

    async def _to_out(self, db: AsyncSession, role: Role) -> dict:
        return {
            "id": role.id,
            "name": role.name,
            "slug": role.slug,
            "description": role.description,
            "is_system": bool(role.is_system),
            "is_active": bool(role.is_active),
            "parent_id": role.parent_id,
            "data_scope": role.data_scope,
            "created_at": role.created_at,
            "permission_count": await self._count_capabilities(db, role.id),
            "user_count": await self._count_users(db, role.id),
        }

    async def list_roles(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_system: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        items, total = await role_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"is_system": is_system, "is_active": is_active},
            order_by="id",
            order="asc",
        )
        return [await self._to_out(db, role) for role in items], total

    async def get_role(self, db: AsyncSession, role_id: int) -> Role:
        role = await role_crud.get(db, role_id)
        if role is None:
            raise NotFoundError("角色不存在")
        return role

    async def get_role_out(self, db: AsyncSession, role_id: int) -> dict:
        return await self._to_out(db, await self.get_role(db, role_id))

    async def create_role(self, db: AsyncSession, payload: RoleCreate) -> dict:
        if await role_crud.exists(db, slug=payload.slug):
            raise ConflictError(f"角色标识 {payload.slug} 已存在")

        role = await role_crud.create(
            db,
            {
                "name": payload.name,
                "slug": payload.slug,
                "description": payload.description,
                "parent_id": payload.parent_id,
                "is_system": False,
                "is_active": True,
            },
        )
        if payload.permission_codes:
            await self.set_permissions(db, role.id, payload.permission_codes)
        await invalidate_all()
        return await self._to_out(db, role)

    async def update_role(self, db: AsyncSession, role_id: int, payload: RoleUpdate) -> dict:
        role = await self.get_role(db, role_id)
        data = payload.model_dump(exclude_unset=True)
        if data.get("parent_id") == role_id:
            raise BadRequestError("父角色不能是自己")
        if role.is_system and "name" in data and not data["name"]:
            raise BadRequestError("系统角色的名称不能为空")
        role = await role_crud.update(db, role, data)
        # 父角色变更会影响继承，直接清空全部权限缓存（角色变更是低频操作）
        await invalidate_all()
        return await self._to_out(db, role)

    async def delete_role(self, db: AsyncSession, role_id: int) -> None:
        role = await self.get_role(db, role_id)
        if role.is_system:
            raise BadRequestError("系统内置角色不可删除")

        user_count = await self._count_users(db, role_id)
        if user_count:
            raise ConflictError(f"仍有 {user_count} 个用户使用该角色，请先解绑")

        await db.execute(RoleCapability.__table__.delete().where(RoleCapability.role_id == role_id))
        await role_crud.remove(db, role)
        await invalidate_all()

    async def get_permissions(self, db: AsyncSession, role_id: int) -> List[str]:
        await self.get_role(db, role_id)
        stmt = (
            select(Capability.code)
            .join(RoleCapability, RoleCapability.capability_id == Capability.id)
            .where(RoleCapability.role_id == role_id)
        )
        return sorted((await db.execute(stmt)).scalars().all())

    async def get_permission_objects(self, db: AsyncSession, role_id: int) -> List[Capability]:
        stmt = (
            select(Capability)
            .join(RoleCapability, RoleCapability.capability_id == Capability.id)
            .where(RoleCapability.role_id == role_id)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def set_permissions(
        self, db: AsyncSession, role_id: int, codes: Sequence[str]
    ) -> List[str]:
        """全量覆盖角色权限（未知权限码直接报错，避免静默丢权限）"""
        role = await self.get_role(db, role_id)
        target_codes = {code.strip() for code in codes if code and code.strip()}

        caps: list[Capability] = []
        if target_codes:
            result = await db.execute(select(Capability).where(Capability.code.in_(target_codes)))
            caps = list(result.scalars().all())
            unknown = target_codes - {cap.code for cap in caps}
            if unknown:
                raise BadRequestError(f"未知权限码: {', '.join(sorted(unknown))}")

        await db.execute(RoleCapability.__table__.delete().where(RoleCapability.role_id == role.id))
        for cap in caps:
            db.add(RoleCapability(role_id=role.id, capability_id=cap.id))
        await db.commit()
        await invalidate_all()
        return await self.get_permissions(db, role.id)


role_service = RoleService()
