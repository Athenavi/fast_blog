# -*- coding: utf-8 -*-
"""后台授权边界：不能创建/管理超管，也不能授出高于自身的权限。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v3.core.exceptions import ForbiddenError
from src.api.v3.core.permission.guard import (
    assert_can_assign_roles,
    assert_can_grant_codes,
    assert_can_manage_user,
)

pytestmark = pytest.mark.unit

_RBAC = "shared.services.security.rbac_service.rbac_service"


def _actor(codes, *, superuser=False):
    actor = MagicMock()
    actor.id = 1
    actor.is_superuser = superuser
    return actor, codes


class TestGrantCodes:
    pytestmark = pytest.mark.asyncio

    async def test_cannot_grant_code_not_owned(self):
        actor, codes = _actor({"article.edit"})
        with patch(f"{_RBAC}.get_permission_codes_set", AsyncMock(return_value=codes)):
            with pytest.raises(ForbiddenError):
                await assert_can_grant_codes(AsyncMock(), actor, {"article.edit", "setting.edit"})

    async def test_subset_is_allowed(self):
        actor, codes = _actor({"article.edit", "setting.view"})
        with patch(f"{_RBAC}.get_permission_codes_set", AsyncMock(return_value=codes)):
            await assert_can_grant_codes(AsyncMock(), actor, {"article.edit"})

    async def test_wildcard_actor_can_grant_anything(self):
        actor, codes = _actor({"*"})
        with patch(f"{_RBAC}.get_permission_codes_set", AsyncMock(return_value=codes)):
            await assert_can_grant_codes(AsyncMock(), actor, {"setting.edit"})

    async def test_superuser_bypasses(self):
        actor, _ = _actor(set(), superuser=True)
        await assert_can_grant_codes(AsyncMock(), actor, {"setting.edit"})


class TestAssignRoles:
    pytestmark = pytest.mark.asyncio

    async def test_role_with_wildcard_requires_superuser(self):
        actor, codes = _actor({"article.edit"})
        with patch(f"{_RBAC}.get_permission_codes_set", AsyncMock(return_value=codes)), \
                patch(f"{_RBAC}.get_role_codes_set", AsyncMock(return_value={"*"})):
            with pytest.raises(ForbiddenError):
                await assert_can_assign_roles(AsyncMock(), actor, [2])

    async def test_role_beyond_actor_is_rejected(self):
        actor, codes = _actor({"article.edit"})
        with patch(f"{_RBAC}.get_permission_codes_set", AsyncMock(return_value=codes)), \
                patch(f"{_RBAC}.get_role_codes_set", AsyncMock(return_value={"setting.edit"})):
            with pytest.raises(ForbiddenError):
                await assert_can_assign_roles(AsyncMock(), actor, [2])

    async def test_role_within_actor_is_allowed(self):
        actor, codes = _actor({"article.edit"})
        with patch(f"{_RBAC}.get_permission_codes_set", AsyncMock(return_value=codes)), \
                patch(f"{_RBAC}.get_role_codes_set", AsyncMock(return_value={"article.edit"})):
            await assert_can_assign_roles(AsyncMock(), actor, [2])


class TestManageSuperuser:
    def test_non_super_cannot_manage_super(self):
        actor = MagicMock(is_superuser=False)
        target = MagicMock(is_superuser=True)
        with pytest.raises(ForbiddenError):
            import asyncio

            asyncio.run(assert_can_manage_user(actor, target))

    def test_super_can_manage_super(self):
        import asyncio

        actor = MagicMock(is_superuser=True)
        target = MagicMock(is_superuser=True)
        asyncio.run(assert_can_manage_user(actor, target))


class TestUserServiceBoundaries:
    pytestmark = pytest.mark.asyncio

    async def test_create_superuser_requires_superuser(self):
        from src.api.v3.modules.system.user.schema import UserCreate
        from src.api.v3.modules.system.user.service import user_service

        actor, _ = _actor({"user.create"})
        payload = UserCreate(
            username="newbie", email="new@example.com", password="pass-1234", is_superuser=True
        )
        with pytest.raises(ForbiddenError):
            await user_service.create_user(AsyncMock(), payload, scope_user=actor)

    async def test_update_superuser_password_requires_superuser(self):
        from src.api.v3.modules.system.user.schema import UserUpdate
        from src.api.v3.modules.system.user.service import user_service

        actor, _ = _actor({"user.edit"})
        target = MagicMock()
        target.id = 9
        target.is_superuser = True
        with patch.object(user_service, "get_user", AsyncMock(return_value=target)):
            with pytest.raises(ForbiddenError):
                await user_service.update_user(
                    AsyncMock(), 9, UserUpdate(password="new-pass-123"), scope_user=actor
                )

    async def test_admin_password_reset_revokes_sessions(self):
        from src.api.v3.modules.system.user.schema import UserUpdate
        from src.api.v3.modules.system.user.service import user_service

        actor, _ = _actor({"user.edit"})
        target = MagicMock()
        target.id = 9
        target.is_superuser = False
        db = AsyncMock()
        with patch.object(user_service, "get_user", AsyncMock(return_value=target)), \
                patch("src.api.v3.modules.system.user.service.set_user_password", AsyncMock()), \
                patch("src.api.v3.core.security.revoke_user_tokens") as revoke:
            await user_service.update_user(
                db, 9, UserUpdate(password="new-pass-123"), scope_user=actor
            )
        revoke.assert_called_once_with(9)

    async def test_assign_escalating_role_is_rejected(self):
        from src.api.v3.modules.system.user.service import user_service

        actor, codes = _actor({"article.edit"})
        target = MagicMock(id=9, is_superuser=False)
        with patch.object(user_service, "get_user", AsyncMock(return_value=target)), \
                patch(f"{_RBAC}.get_permission_codes_set", AsyncMock(return_value=codes)), \
                patch(f"{_RBAC}.get_role_codes_set", AsyncMock(return_value={"setting.edit"})):
            with pytest.raises(ForbiddenError):
                await user_service.set_user_roles(AsyncMock(), 9, [2], scope_user=actor)


class TestRoleServiceBoundaries:
    pytestmark = pytest.mark.asyncio

    async def test_cannot_overwrite_higher_role(self):
        from src.api.v3.modules.system.role.service import role_service

        actor, codes = _actor({"role.edit"})
        role = MagicMock(id=3)
        with patch.object(role_service, "get_role", AsyncMock(return_value=role)), \
                patch(f"{_RBAC}.get_permission_codes_set", AsyncMock(return_value=codes)), \
                patch(f"{_RBAC}.get_role_codes_set", AsyncMock(return_value={"setting.edit"})):
            with pytest.raises(ForbiddenError):
                await role_service.set_permissions(
                    AsyncMock(), 3, ["role.edit"], scope_user=actor
                )

    async def test_cannot_grant_code_not_owned(self):
        from src.api.v3.modules.system.role.service import role_service

        actor, codes = _actor({"role.edit"})
        role = MagicMock(id=3)
        with patch.object(role_service, "get_role", AsyncMock(return_value=role)), \
                patch(f"{_RBAC}.get_permission_codes_set", AsyncMock(return_value=codes)), \
                patch(f"{_RBAC}.get_role_codes_set", AsyncMock(return_value=set())):
            with pytest.raises(ForbiddenError):
                await role_service.set_permissions(
                    AsyncMock(), 3, ["setting.edit"], scope_user=actor
                )
