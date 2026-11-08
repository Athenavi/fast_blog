# -*- coding: utf-8 -*-
"""
Authentication dependencies — unit tests.

Covers:
  - create_access_token: JWT generation
  - _get_token_from_request: token extraction (header / cookie)
  - _authenticate_user: core auth logic (valid/invalid/expired/blacklisted/inactive)
  - get_current_user: authenticated user retrieval
  - admin_required: superuser check
  - jwt_optional_dependency: optional auth

WHY these tests exist:
  The auth layer protects every API endpoint. A regression here can
  silently grant unauthorized access or lock out legitimate users.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import HTTPException, Request

from src.auth.auth_deps import (
    create_access_token,
    _get_token_from_request,
    _authenticate_user,
    get_current_user,
    admin_required,
    jwt_optional_dependency,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_request():
    """Minimal FastAPI Request mock with headers and cookies."""
    req = MagicMock(spec=Request)
    req.headers = {}
    req.cookies = {}
    # query_params must return None for .get("token") so the function
    # doesn't short-circuit on a falsy MagicMock before reaching cookies
    req.query_params = {}
    return req


@pytest.fixture
def mock_db():
    """Async database session mock that returns no user by default.

    IMPORTANT: `result` is a regular MagicMock because `scalar_one_or_none()`
    is called synchronously (not awaited) by the auth code.
    """
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    return db


@pytest.fixture
def active_user():
    """A normal active user (not superuser, not staff)."""
    user = MagicMock()
    user.id = 1
    user.is_active = True
    user.is_superuser = False
    user.is_staff = False
    user.has_permission.return_value = False
    user.has_role.return_value = False
    return user


@pytest.fixture
def admin_user():
    """An active superuser."""
    user = MagicMock()
    user.id = 1
    user.is_active = True
    user.is_superuser = True
    user.has_permission.return_value = True
    user.has_role.return_value = True
    return user


@pytest.fixture
def valid_token():
    """A valid JWT token string (mocked, not cryptographically signed)."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.valid-token"


# ============================================================================
# create_access_token
# ============================================================================

class TestCreateAccessToken:
    """JWT access token generation."""

    @patch("src.auth.auth_deps.jwt.encode")
    @patch("src.auth.auth_deps.settings")
    def test_creates_token_with_default_lifetime(self, mock_settings, mock_encode):
        """Uses default JWT_EXPIRATION_MINUTES when lifetime not provided."""
        mock_settings.JWT_EXPIRATION_MINUTES = 60
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "fallback-secret"
        mock_encode.return_value = "generated-token"

        token = create_access_token(user_id=1)

        assert token == "generated-token"
        _, kwargs = mock_encode.call_args
        assert kwargs["algorithm"] == "HS256"
        # Verify payload has sub, iat, exp
        payload = kwargs["algorithm"]  # no, that's wrong
        payload = mock_encode.call_args.args[0]
        assert payload["sub"] == "1"

    @patch("src.auth.auth_deps.jwt.encode")
    @patch("src.auth.auth_deps.settings")
    def test_creates_token_with_custom_lifetime(self, mock_settings, mock_encode):
        """Uses provided lifetime when specified."""
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "fallback-secret"
        mock_encode.return_value = "token"

        lifetime = datetime.timedelta(hours=2)
        create_access_token(user_id=42, lifetime=lifetime)

        payload = mock_encode.call_args.args[0]
        assert payload["sub"] == "42"

    @patch("src.auth.auth_deps.jwt.encode")
    @patch("src.auth.auth_deps.settings")
    def test_uses_fallback_secret_key(self, mock_settings, mock_encode):
        """Falls back to SECRET_KEY when JWT_SECRET_KEY is not set."""
        mock_settings.JWT_EXPIRATION_MINUTES = 60
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "fallback-secret"
        mock_encode.return_value = "token"

        # Remove JWT_SECRET_KEY to force getattr fallback to SECRET_KEY
        mock_settings.JWT_SECRET_KEY = "unused"
        del mock_settings.JWT_SECRET_KEY

        create_access_token(user_id=1)

        _, kwargs = mock_encode.call_args
        assert kwargs["algorithm"] == "HS256"


# ============================================================================
# _get_token_from_request
# ============================================================================

class TestGetTokenFromRequest:
    pytestmark = pytest.mark.asyncio

    """Token extraction from request headers/cookies."""

    async def test_from_bearer_header(self, mock_request):
        """Extracts token from Authorization: Bearer header."""
        mock_request.headers = {"Authorization": "Bearer my-secret-token"}
        token = await _get_token_from_request(mock_request)
        assert token == "my-secret-token"

    # NOTE: Case-insensitivity is a Starlette/FASTAPI Request.headers feature,
    # not tested here because mock uses plain dict (case-sensitive).

    async def test_from_cookie(self, mock_request):
        """Falls back to access_token cookie when no header."""
        mock_request.cookies = {"access_token": "cookie-token"}
        token = await _get_token_from_request(mock_request)
        assert token == "cookie-token"

    async def test_from_access_token_cookie_fallback(self, mock_request):
        """Falls back to access_token_cookie cookie name."""
        mock_request.cookies = {"access_token_cookie": "alt-cookie-token"}
        token = await _get_token_from_request(mock_request)
        assert token == "alt-cookie-token"

    async def test_header_takes_precedence_over_cookie(self, mock_request):
        """Bearer header is preferred over cookie."""
        mock_request.headers = {"Authorization": "Bearer header-token"}
        mock_request.cookies = {"access_token": "cookie-token"}
        token = await _get_token_from_request(mock_request)
        assert token == "header-token"

    async def test_no_token_returns_none(self, mock_request):
        """No Authorization header and no cookie → None."""
        token = await _get_token_from_request(mock_request)
        assert token is None

    async def test_rejects_non_bearer_auth_header(self, mock_request):
        """Authorization header that doesn't start with 'Bearer ' is ignored."""
        mock_request.headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        token = await _get_token_from_request(mock_request)
        assert token is None  # Falls through to cookie


# ============================================================================
# _authenticate_user
# ============================================================================

class TestAuthenticateUser:
    pytestmark = pytest.mark.asyncio

    """Core authentication logic (mocked JWT + DB)."""

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_valid_token_returns_user(
        self, mock_settings, mock_decode, mock_request, mock_db, active_user
    ):
        """Valid, non-expired token returns the user from DB."""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.return_value = {"sub": "1", "type": "access"}

        # Set bearer token so _get_token_from_request returns it
        mock_request.headers = {"Authorization": "Bearer valid-token"}
        # Make the DB query return active_user
        mock_db.execute.return_value.scalar_one_or_none.return_value = active_user

        user = await _authenticate_user(mock_request, mock_db, required=True)

        assert user is active_user
        mock_decode.assert_called_once()

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_refresh_token_rejected_as_access(
        self, mock_settings, mock_decode, mock_request, mock_db, active_user
    ):
        """refresh 令牌不能当访问令牌用：它有效期 30 天，签名与 access 完全一样。"""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.return_value = {"sub": "1", "type": "refresh"}
        mock_request.headers = {"Authorization": "Bearer refresh-token"}
        mock_db.execute.return_value.scalar_one_or_none.return_value = active_user

        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_temp_2fa_token_rejected(
        self, mock_settings, mock_decode, mock_request, mock_db, active_user
    ):
        """2FA 未完成时下发的 temp_2fa 令牌必须被拒，否则 2FA 可被整个旁路。"""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.return_value = {"sub": "1", "type": "temp_2fa"}
        mock_request.headers = {"Authorization": "Bearer temp-token"}
        mock_db.execute.return_value.scalar_one_or_none.return_value = active_user

        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401
        # 可选鉴权（公开接口的 viewer）同样不能把它当成登录态
        assert await _authenticate_user(mock_request, mock_db, required=False) is None

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_no_token_raises_401_when_required(
        self, mock_settings, mock_decode, mock_request, mock_db
    ):
        """Missing token raises 401 when required=True."""
        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401

    async def test_no_token_returns_none_when_optional(
        self, mock_request, mock_db
    ):
        """Missing token returns None when required=False."""
        user = await _authenticate_user(mock_request, mock_db, required=False)
        assert user is None

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_invalid_token_raises_401(
        self, mock_settings, mock_decode, mock_request, mock_db
    ):
        """Invalid/expired token raises 401."""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_request.headers = {"Authorization": "Bearer expired-token"}
        mock_decode.side_effect = pyjwt.InvalidTokenError("Token expired")

        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_invalid_token_returns_none_when_optional(
        self, mock_settings, mock_decode, mock_request, mock_db
    ):
        """Invalid token returns None when required=False."""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.side_effect = pyjwt.InvalidTokenError("bad token")

        user = await _authenticate_user(mock_request, mock_db, required=False)
        assert user is None

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_missing_subject_raises_401(
        self, mock_settings, mock_decode, mock_request, mock_db
    ):
        """Token with no 'sub' claim raises 401."""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.return_value = {}  # No sub

        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_non_integer_sub_raises_401(
        self, mock_settings, mock_decode, mock_request, mock_db
    ):
        """Non-numeric sub raises 401."""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.return_value = {"sub": "not-a-number"}

        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_user_not_found_raises_401(
        self, mock_settings, mock_decode, mock_request, mock_db
    ):
        """Valid token but user doesn't exist in DB → 401."""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.return_value = {"sub": "999", "type": "access"}  # Non-existent user
        # DB query returns None (default fixture)

        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_inactive_user_raises_401(
        self, mock_settings, mock_decode, mock_request, mock_db
    ):
        """Deactivated user → 401."""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.return_value = {"sub": "1", "type": "access"}

        inactive_user = MagicMock()
        inactive_user.is_active = False
        mock_db.execute.return_value.scalar_one_or_none.return_value = inactive_user

        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps._get_token_blacklist")
    @patch("src.auth.auth_deps.settings")
    async def test_blacklisted_token_raises_401(
        self, mock_settings, mock_bl, mock_decode, mock_request, mock_db
    ):
        """Token in blacklist → 401."""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_request.headers = {"Authorization": "Bearer revoked-token"}
        mock_decode.return_value = {"sub": "1", "jti": "revoked-jti", "type": "access"}

        mock_blacklist = MagicMock()
        mock_blacklist.is_available = True
        mock_blacklist.is_blacklisted_async = AsyncMock(return_value=True)
        mock_bl.return_value = mock_blacklist

        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401

    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_auth_with_bearer_header(
        self, mock_settings, mock_decode, mock_request, mock_db, active_user
    ):
        """Full flow: Bearer token → decode → DB query → return user."""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.return_value = {"sub": "1", "type": "access"}
        mock_request.headers = {"Authorization": "Bearer my-valid-token"}
        mock_db.execute.return_value.scalar_one_or_none.return_value = active_user

        user = await _authenticate_user(mock_request, mock_db, required=True)

        assert user is active_user


# ============================================================================
# get_current_user
# ============================================================================

class TestGetCurrentUser:
    pytestmark = pytest.mark.asyncio

    """Required auth dependency."""

    @patch("src.auth.auth_deps._authenticate_user")
    async def test_returns_user(self, mock_auth, mock_request, mock_db, active_user):
        """Valid auth returns the user."""
        mock_auth.return_value = active_user
        user = await get_current_user(mock_request, db=mock_db)
        assert user is active_user
        mock_auth.assert_called_once_with(mock_request, mock_db, required=True)

    @patch("src.auth.auth_deps._authenticate_user")
    async def test_raises_when_unauthenticated(self, mock_auth, mock_request, mock_db):
        """No auth raises HTTPException 401."""
        mock_auth.side_effect = HTTPException(status_code=401, detail="Not authenticated")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(mock_request, db=mock_db)
        assert exc.value.status_code == 401


# ============================================================================
# admin_required
# ============================================================================

class TestAdminRequired:
    pytestmark = pytest.mark.asyncio

    """Superuser check."""

    async def test_admin_user_passes(self, admin_user):
        """Superuser passes the check."""
        user = await admin_required(user=admin_user)
        assert user is admin_user

    async def test_non_admin_raises_403(self, active_user):
        """Non-superuser raises 403."""
        with pytest.raises(HTTPException) as exc:
            await admin_required(user=active_user)
        assert exc.value.status_code == 403
        assert "Insufficient privileges" in exc.value.detail


# ============================================================================
# jwt_optional_dependency
# ============================================================================

class TestJWTOptional:
    pytestmark = pytest.mark.asyncio

    """Optional auth: returns None when no valid token."""

    @patch("src.auth.auth_deps._authenticate_user")
    async def test_with_valid_token(self, mock_auth, mock_request, mock_db, active_user):
        """Valid token returns the user."""
        mock_auth.return_value = active_user
        user = await jwt_optional_dependency(mock_request, db=mock_db)
        assert user is active_user
        mock_auth.assert_called_once_with(mock_request, mock_db, required=False)

    @patch("src.auth.auth_deps._authenticate_user")
    async def test_without_token(self, mock_auth, mock_request, mock_db):
        """No token returns None."""
        mock_auth.return_value = None
        user = await jwt_optional_dependency(mock_request, db=mock_db)
        assert user is None


# ============================================================================
# revoke_token（登出）
# ============================================================================

class TestRevokeToken:
    """登出必须真的写进黑名单，且写键与读取侧（jti）一致。"""

    @patch("src.api.v3.core.security.get_token_blacklist")
    def test_revoke_writes_jti_key(self, mock_get_blacklist):
        """写黑名单用 jti，过期时间按本地时间还原（对齐 add_to_blacklist 的 TTL 算法）。"""
        from src.api.v3.core.security import issue_token, revoke_token

        token = issue_token("7", "access", datetime.timedelta(minutes=30))
        payload = pyjwt.decode(token, key=None, options={"verify_signature": False})

        blacklist = MagicMock()
        blacklist.is_available = True
        # `decode_token` 会先查黑名单与用户水位线：这个令牌尚未吊销，必须都返回 False
        blacklist.is_blacklisted.return_value = False
        blacklist.is_user_revoked.return_value = False
        blacklist.add_to_blacklist.return_value = True
        mock_get_blacklist.return_value = blacklist

        assert revoke_token(token) is True

        written_token, written_exp = blacklist.add_to_blacklist.call_args.args
        # 读取侧 `is_blacklisted(jti)`：写键必须是 jti，否则永远查不到
        assert written_token == payload["jti"]
        # TTL 用于 Redis 过期时间；相差一天以上就是时区算错了（令牌会立刻失效或永不过期）
        assert abs(written_exp.timestamp() - payload["exp"]) < 60

    @patch("src.api.v3.core.security.get_token_blacklist")
    def test_revoke_without_jti_returns_false(self, mock_get_blacklist):
        """没有 jti 的令牌无法吊销，返回 False 而不是假装成功。"""
        from src.api.v3.core.security import revoke_token

        blacklist = MagicMock()
        blacklist.is_available = True
        mock_get_blacklist.return_value = blacklist

        assert revoke_token("not-a-jwt") is False
        blacklist.add_to_blacklist.assert_not_called()


# ============================================================================
# 用户级吊销水位线（退出所有设备）
# ============================================================================

class _FakeRedis:
    """最小 Redis 替身：只实现水位线用到的 get/setex。"""

    def __init__(self):
        self.store = {}

    def setex(self, key, ttl, value):
        self.store[key] = str(value)
        return True

    def get(self, key):
        return self.store.get(key)


class TestUserRevocationWatermark:
    def _manager(self, enabled=True):
        from src.utils.token_blacklist import TokenBlacklistManager

        m = TokenBlacklistManager.__new__(TokenBlacklistManager)
        m.redis_enabled = enabled
        m.redis_client = _FakeRedis() if enabled else None
        return m

    def test_invalidates_older_tokens_only(self):
        import time

        m = self._manager()
        assert m.revoke_user_tokens(7, datetime.datetime.now() + datetime.timedelta(hours=1)) is True

        # 吊销之前签发的：失效
        assert m.is_user_revoked(7, time.time() - 60) is True
        # 吊销之后签发的（重新登录）：不受影响
        assert m.is_user_revoked(7, time.time() + 60) is False
        # 其他用户完全不受影响
        assert m.is_user_revoked(8, time.time() - 60) is False

    def test_disabled_without_redis(self):
        """Redis 不可用时不能谎报成功，也不能把所有人锁在门外。"""
        m = self._manager(enabled=False)
        assert m.revoke_user_tokens(1, datetime.datetime.now()) is False
        assert m.is_user_revoked(1, 0) is False


class TestAuthenticateUserWatermark:
    pytestmark = pytest.mark.asyncio

    @patch("src.auth.auth_deps._get_token_blacklist")
    @patch("src.auth.auth_deps.jwt.decode")
    @patch("src.auth.auth_deps.settings")
    async def test_watermark_rejects_token(
        self, mock_settings, mock_decode, mock_get_blacklist, mock_request, mock_db, active_user
    ):
        """登出（退出所有设备）之后，旧令牌不能再通过鉴权。"""
        mock_settings.JWT_SECRET_KEY = "secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.SECRET_KEY = "secret"
        mock_decode.return_value = {"sub": "1", "type": "access", "iat": 1000, "jti": "j1"}
        mock_request.headers = {"Authorization": "Bearer old-token"}

        blacklist = MagicMock()
        blacklist.is_available = True
        blacklist.is_blacklisted_async = AsyncMock(return_value=False)
        blacklist.is_user_revoked_async = AsyncMock(return_value=True)
        mock_get_blacklist.return_value = blacklist

        with pytest.raises(HTTPException) as exc:
            await _authenticate_user(mock_request, mock_db, required=True)
        assert exc.value.status_code == 401
        blacklist.is_user_revoked_async.assert_awaited_once_with(1, 1000.0)
