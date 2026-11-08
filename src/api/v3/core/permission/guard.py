"""授权边界：谁能把权限/角色/超管身份授予别人。

后台的"管理用户 / 管理角色"本身就是高权限操作。如果没有下面这些约束，
一个被授予 `user:create` 或 `role:edit` 的管理员可以给自己（或小号）开出
超级管理员身份，等于绕过全部权限设计。

规则：
  - 只有超管能创建 / 管理**超管账号**；
  - 授予的权限码（含角色继承后的有效码）必须是发起者自身权限的子集；
    持有通配码（``*`` / ``*:*:*``）视为拥有全部权限；
  - 修改角色权限时，角色的**现有**权限也必须在发起者权限之内 ——
    否则低权限者可以篡改/剥离高权限角色。
"""

from __future__ import annotations

from typing import Any, Iterable, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import ForbiddenError
from src.api.v3.core.permission.constants import WILDCARD_CODES


def is_superuser(actor: Any) -> bool:
    return bool(getattr(actor, "is_superuser", False))


async def actor_codes(db: AsyncSession, actor: Any) -> set[str]:
    from shared.services.security.rbac_service import rbac_service

    return set(await rbac_service.get_permission_codes_set(db, int(actor.id)))


async def assert_can_grant_codes(
    db: AsyncSession, actor: Any, codes: Iterable[str], *, what: str = "权限"
) -> None:
    """发起者只能授予自己已经拥有的权限码。"""
    if is_superuser(actor):
        return
    owned = await actor_codes(db, actor)
    if owned & WILDCARD_CODES:
        return
    overflow = sorted({str(code).strip() for code in codes if str(code).strip()} - owned)
    if overflow:
        raise ForbiddenError(
            f"不能授予超出自身权限的{what}：" + "、".join(overflow)
        )


async def assert_can_assign_roles(
    db: AsyncSession, actor: Any, role_ids: Iterable[int]
) -> None:
    """分配角色时，角色的**有效权限**（含父角色）必须都在发起者权限之内。"""
    if is_superuser(actor):
        return
    ids: List[int] = [int(role_id) for role_id in role_ids]
    if not ids:
        return
    from shared.services.security.rbac_service import rbac_service

    codes = await rbac_service.get_role_codes_set(db, ids)
    if codes & WILDCARD_CODES:
        raise ForbiddenError("该角色包含通配权限，只有超级管理员可以分配")
    await assert_can_grant_codes(db, actor, codes, what="角色权限")


async def assert_can_manage_user(actor: Any, target: Any) -> None:
    """非超管不得管理超管账号（改密码、停用、删除、改角色都不行）。"""
    if target is None:
        return
    if bool(getattr(target, "is_superuser", False)) and not is_superuser(actor):
        raise ForbiddenError("只有超级管理员可以管理超级管理员账号")
