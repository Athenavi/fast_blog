"""user 模块业务逻辑

复用 ``shared/services/users`` 已有的用户能力（账号创建、资料更新、密码重置、启停）
与 ``rbac_service`` 的角色分配，不重复实现。
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from shared.services.security.rbac_service import rbac_service
from shared.services.users.user_manager import (
    activate_user,
    create_user_account,
    deactivate_user,
    search_users,
    set_user_password,
    update_user_profile,
)
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.invalidate import invalidate_user
from src.api.v3.modules.system.user.crud import user_crud
from src.api.v3.modules.system.user.schema import UserCreate, UserUpdate

logger = get_logger("user")


class UserService:
    """用户管理服务"""

    async def list_users(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
    ) -> tuple[list[User], int]:
        """分页查询用户（关键词模糊匹配用户名/邮箱）"""
        result = await search_users(
            db,
            keyword or "",
            page=page,
            per_page=page_size,
            is_active=is_active,
            is_superuser=is_superuser,
        )
        if isinstance(result, tuple) and len(result) == 2:
            items, total = result
            return list(items), int(total)
        # 兜底：service 返回结构变化时不至于 500
        return await user_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"is_active": is_active, "is_superuser": is_superuser},
            order_by="id",
        )

    async def get_user(self, db: AsyncSession, user_id: int) -> User:
        user = await user_crud.get(db, user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        return user

    async def create_user(self, db: AsyncSession, payload: UserCreate) -> User:
        data = payload.model_dump(exclude={"role_ids"})
        user = await create_user_account(db, **data)
        if user is None:
            raise BadRequestError("创建用户失败（用户名或邮箱可能已存在）")
        await db.commit()
        await db.refresh(user)

        for role_id in payload.role_ids:
            await rbac_service.assign_role_by_id(db, user.id, role_id)
        return user

    async def update_user(self, db: AsyncSession, user_id: int, payload: UserUpdate) -> User:
        user = await self.get_user(db, user_id)
        data = payload.model_dump(exclude_unset=True)
        password = data.pop("password", None)

        if data:
            await update_user_profile(db, user_id, **data)
        if password:
            await set_user_password(db, user_id, password)

        await db.commit()
        await db.refresh(user)
        return user

    async def delete_user(
        self,
        db: AsyncSession,
        user_id: int,
        current_user_id: int,
        *,
        force: bool = False,
    ) -> None:
        """删除用户：默认停用（保留数据），``force=True`` 时物理删除"""
        if user_id == current_user_id:
            raise BadRequestError("不能删除当前登录账号")

        user = await self.get_user(db, user_id)
        if force:
            await user_crud.remove(db, user)
            # 用户被删除后必须清掉其权限缓存，否则残留缓存会继续放行
            await invalidate_user(user_id)
            return

        await deactivate_user(db, user_id)
        await db.refresh(user)

    async def set_status(self, db: AsyncSession, user_id: int, is_active: bool) -> User:
        user = await self.get_user(db, user_id)
        if is_active:
            await activate_user(db, user_id)
        else:
            await deactivate_user(db, user_id)
        await db.refresh(user)
        return user

    async def get_user_roles(self, db: AsyncSession, user_id: int) -> List[dict]:
        await self.get_user(db, user_id)
        roles = await rbac_service.get_user_roles(db, user_id)
        return [{"id": role.id, "name": role.name, "slug": role.slug} for role in roles]

    async def set_user_roles(self, db: AsyncSession, user_id: int, role_ids: List[int]) -> List[dict]:
        """全量覆盖用户角色（差量增删，避免整表重写）"""
        await self.get_user(db, user_id)
        current = {role.id for role in await rbac_service.get_user_roles(db, user_id)}
        target = set(role_ids)

        for role_id in target - current:
            await rbac_service.assign_role_by_id(db, user_id, role_id)
        for role_id in current - target:
            await rbac_service.remove_role_by_id(db, user_id, role_id)

        await invalidate_user(user_id)
        return await self.get_user_roles(db, user_id)

    async def get_user_permissions(self, db: AsyncSession, user_id: int) -> List[str]:
        await self.get_user(db, user_id)
        return sorted(await rbac_service.get_permission_codes_set(db, user_id))


user_service = UserService()
