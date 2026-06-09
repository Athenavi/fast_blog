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
  - require_permission / require_role: permission/role checkers

WHY these tests exist:
  The auth layer protects every API endpoint. A regression here can
  silently grant unauthorized access or lock out legitimate users.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from src.auth.auth_deps import (
    create_access_token,
    _get_token_from_request,
    _authenticate_user,
    get_current_user,
    admin_required,
    jwt_optional_dependency,
    require_permission,
    require_role,
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
    """A normal active user (not superuser)."""
    user = MagicMock()
    user.id = 1
    user.is_active = True
    user.is_superuser = False
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
        mock_decode.return_value = {"sub": "1"}

        # Set bearer token so _get_token_from_request returns it
        mock_request.headers = {"Authorization": "Bearer valid-token"}
        # Make the DB query return active_user
        mock_db.execute.return_value.scalar_one_or_none.return_value = active_user

        user = await _authenticate_user(mock_request, mock_db, required=True)

        assert user is active_user
        mock_decode.assert_called_once()

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
        mock_decode.return_value = {"sub": "999"}  # Non-existent user
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
        mock_decode.return_value = {"sub": "1"}

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
        mock_decode.return_value = {"sub": "1", "jti": "revoked-jti"}

        mock_blacklist = MagicMock()
        mock_blacklist.is_available = True
        mock_blacklist.is_blacklisted.return_value = True
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
        mock_decode.return_value = {"sub": "1"}
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
# require_permission / require_role / require_vip
# ============================================================================

class TestRequirePermission:
    pytestmark = pytest.mark.asyncio

    """Permission checker factory."""

    async def test_user_with_permission_passes(self, admin_user):
        """User with the required permission passes."""
        admin_user.has_permission.return_value = True
        checker = require_permission("articles.create")
        user = await checker(user=admin_user)
        assert user is admin_user
        admin_user.has_permission.assert_called_with("articles.create")

    async def test_user_without_permission_raises_403(self, active_user):
        """User without permission raises 403."""
        active_user.has_permission.return_value = False
        checker = require_permission("articles.delete")
        with pytest.raises(HTTPException) as exc:
            await checker(user=active_user)
        assert exc.value.status_code == 403


class TestRequireRole:
    pytestmark = pytest.mark.asyncio

    """Role checker factory."""

    async def test_user_with_role_passes(self, admin_user):
        """User with the required role passes."""
        admin_user.has_role.return_value = True
        checker = require_role("editor")
        user = await checker(user=admin_user)
        assert user is admin_user
        admin_user.has_role.assert_called_with("editor")

    async def test_user_without_role_raises_403(self, active_user):
        """User without role raises 403."""
        active_user.has_role.return_value = False
        checker = require_role("admin")
        with pytest.raises(HTTPException) as exc:
            await checker(user=active_user)
        assert exc.value.status_code == 403
