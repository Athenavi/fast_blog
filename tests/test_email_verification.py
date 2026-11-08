# -*- coding: utf-8 -*-
"""OAuth 自助建号的 24 小时邮箱验证窗口。"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v3.modules.system.auth.service import auth_service, email_verification_expired

pytestmark = pytest.mark.unit


def _user(**overrides):
    user = MagicMock()
    user.id = 7
    user.email = "u@example.com"
    user.is_email_verified = False
    user.date_joined = datetime.now() - timedelta(hours=1)
    for key, value in overrides.items():
        setattr(user, key, value)
    return user


class TestGraceWindow:
    def test_within_24h_is_not_expired(self):
        assert email_verification_expired(_user()) is False

    def test_past_24h_is_expired(self):
        user = _user(date_joined=datetime.now() - timedelta(hours=25))
        assert email_verification_expired(user) is True

    def test_verified_account_never_expires(self):
        user = _user(
            is_email_verified=True, date_joined=datetime.now() - timedelta(days=30)
        )
        assert email_verification_expired(user) is False

    def test_account_without_email_is_exempt(self):
        """微信/QQ/微博不返回邮箱，无从验证，不能被 24h 规则永久锁死。"""
        user = _user(email=None, date_joined=datetime.now() - timedelta(days=30))
        assert email_verification_expired(user) is False


class TestVerifyEmail:
    pytestmark = pytest.mark.asyncio

    async def test_verify_token_marks_account_verified(self):
        user = _user()
        db = AsyncMock()
        db.get = AsyncMock(return_value=user)

        with patch(
            "src.api.v3.modules.system.auth.service.decode_token_async",
            AsyncMock(return_value={"sub": "7", "type": "email_verify"}),
        ):
            result = await auth_service.verify_email(db, "token")

        assert result is user
        assert user.is_email_verified is True
        db.commit.assert_awaited_once()

    async def test_access_token_is_rejected(self):
        from src.api.v3.core.exceptions import UnauthorizedError

        with patch(
            "src.api.v3.modules.system.auth.service.decode_token_async",
            AsyncMock(return_value={"sub": "7", "type": "access"}),
        ):
            with pytest.raises(UnauthorizedError):
                await auth_service.verify_email(AsyncMock(), "token")


class TestSendVerification:
    pytestmark = pytest.mark.asyncio

    def _db(self, user):
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.first.return_value = user
        db.execute = AsyncMock(return_value=result)
        return db

    async def test_sends_for_unverified_account(self):
        user = _user(email="U@Example.com")
        with patch("src.utils.send_email.api_mail", AsyncMock(return_value=True)) as mail:
            sent = await auth_service.send_email_verification(self._db(user), email="u@example.com")

        assert sent is True
        mail.assert_awaited_once()
        assert mail.await_args.kwargs["recipient"] == "U@Example.com"

    async def test_skips_verified_account(self):
        user = _user(is_email_verified=True)
        with patch("src.utils.send_email.api_mail", AsyncMock()) as mail:
            sent = await auth_service.send_email_verification(self._db(user), email="u@example.com")

        assert sent is False
        mail.assert_not_awaited()

    async def test_unknown_email_is_indistinguishable(self):
        """不存在 / 已验证 / 不存在 —— 对外都是同一句提示，不泄露账号是否存在。"""
        with patch("src.utils.send_email.api_mail", AsyncMock()) as mail:
            assert await auth_service.send_email_verification(self._db(None), email="nobody@x.com") is False
        mail.assert_not_awaited()
