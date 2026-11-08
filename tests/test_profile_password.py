# -*- coding: utf-8 -*-
"""个人中心改密码必须校验原密码（`mobile/user/service.py`）。

此前 `PUT /mobile/user/profile` 只要带 `password` 就直接覆盖 —— access token 一旦泄露，
攻击者可以把密码换掉，把所有者永久锁在门外。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.mobile.user.schema import MobileProfileUpdate
from src.api.v3.modules.mobile.user.service import MobileUserService
from src.utils.security.password_validator import hash_password

_SVC = "src.api.v3.modules.mobile.user.service"


def _user():
    user = MagicMock()
    user.id = 1
    user.password = hash_password("old-pass-123")
    return user


class TestProfilePasswordChange:
    pytestmark = pytest.mark.asyncio

    async def test_missing_old_password_is_rejected(self):
        with pytest.raises(BadRequestError, match="原密码"):
            await MobileUserService().update_profile(
                AsyncMock(), _user(), MobileProfileUpdate(password="new-pass-123")
            )

    async def test_wrong_old_password_is_rejected(self):
        with pytest.raises(BadRequestError, match="原密码"):
            await MobileUserService().update_profile(
                AsyncMock(),
                _user(),
                MobileProfileUpdate(password="new-pass-123", old_password="wrong-pass"),
            )

    async def test_correct_old_password_updates(self):
        set_password = AsyncMock()
        db = AsyncMock()
        with patch(f"{_SVC}.set_user_password", set_password), patch(
            f"{_SVC}.update_user_profile", AsyncMock()
        ), patch(f"{_SVC}.auth_service.build_current_user", AsyncMock(return_value={})), patch(
            "src.api.v3.core.security.revoke_user_tokens", return_value=True
        ) as revoke, patch(
            "src.api.v3.core.security.issue_token", side_effect=["new-access", "new-refresh"]
        ):
            result = await MobileUserService().update_profile(
                db,
                _user(),
                MobileProfileUpdate(password="new-pass-123", old_password="old-pass-123"),
            )

        set_password.assert_awaited_once()
        assert set_password.await_args.args[2] == "new-pass-123"
        # 改密必须让其它设备下线，同时给当前端重签一对令牌
        revoke.assert_called_once_with(1)
        assert result["access_token"] == "new-access"
        assert result["refresh_token"] == "new-refresh"

    async def test_no_password_change_does_not_revoke(self):
        """只改资料不该把用户踢下线。"""
        db = AsyncMock()
        with patch(f"{_SVC}.update_user_profile", AsyncMock()), patch(
            f"{_SVC}.auth_service.build_current_user", AsyncMock(return_value={})
        ), patch("src.api.v3.core.security.revoke_user_tokens") as revoke:
            result = await MobileUserService().update_profile(
                db, _user(), MobileProfileUpdate(bio="新的简介")
            )

        revoke.assert_not_called()
        assert "access_token" not in result
