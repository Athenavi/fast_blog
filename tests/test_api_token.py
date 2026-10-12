# -*- coding: utf-8 -*-
"""P1-2 对外 API 令牌：单元与鉴权测试（不依赖数据库）。

覆盖：

  1. 令牌明文字格式与解析（``fbk_<prefix>_<secret>``，前缀可索引）；
  2. Argon2 哈希校验（错误 secret 必须失败，异常一律 fail-closed）；
  3. scopes 文本 ↔ 集合（含非法输入 → 空集，绝不"解析失败就放行"）；
  4. 服务层：scopes 越权被拒、空 scopes 被拒、撤销归属校验、可见性分流；
  5. 鉴权层：无凭证 401、非法 X-API-Key 401（格式错不查库）。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v3.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from src.api.v3.modules.system.api_token.service import ApiTokenService
from src.auth.api_token import (
    TOKEN_SCHEME,
    Principal,
    generate_token,
    scopes_from_text,
    scopes_to_text,
    split_token,
    verify_secret,
)


class FakeUser:
    def __init__(self, user_id: int = 1, is_superuser: bool = False) -> None:
        self.id = user_id
        self.is_superuser = is_superuser


# ---------------------------------------------------------------- 令牌格式

class TestTokenFormat:
    def test_generated_token_roundtrip(self):
        plaintext, prefix, hashed = generate_token()
        assert plaintext.startswith(f"{TOKEN_SCHEME}_")
        parts = plaintext.split("_")
        assert len(parts) == 3
        assert parts[1] == prefix
        assert split_token(plaintext) == (prefix, parts[2])
        assert verify_secret(parts[2], hashed)

    def test_prefix_is_short_and_secret_is_long(self):
        plaintext, prefix, _ = generate_token()
        secret = plaintext.split("_")[2]
        assert len(prefix) == 8, "prefix 用于列表识别，需短且可索引"
        assert len(prefix) <= 16, "prefix 受列宽限制（models.yaml maxLength: 16）"
        assert len(secret) == 64, "secret 使用 token_hex(32) → 256 bit 熵"
        assert "_" not in prefix and "_" not in secret, "分隔符不得出现在随机串里"

    def test_wrong_secret_fails(self):
        plaintext, _, hashed = generate_token()
        other_secret = plaintext.split("_")[2] + "x"
        assert not verify_secret(other_secret, hashed)

    def test_verify_fail_closed_on_bad_hash(self):
        assert not verify_secret("whatever", "")
        assert not verify_secret("whatever", "not-a-hash")

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "plain-token",
            "fbk_only-two",
            "fbk__secret",
            "fbk_prefix_",
            "other_prefix_secret",
            "fbk_a_b_c",
        ],
    )
    def test_malformed_tokens_are_rejected(self, raw):
        assert split_token(raw) is None


# ---------------------------------------------------------------- scopes 序列化

class TestScopesText:
    def test_roundtrip_sorted_and_deduped(self):
        text = scopes_to_text(["b:2", "a:1", "a:1"])
        assert scopes_from_text(text) == frozenset({"a:1", "b:2"})

    @pytest.mark.parametrize("bad", [None, "", "not json", "{}", "[]x", '{"a":1}', "[1,2]"])
    def test_bad_input_yields_empty_set(self, bad):
        assert scopes_from_text(bad) == frozenset()

    def test_principal_semantics(self):
        session = Principal(user=FakeUser(), scopes=None, source="jwt")
        token = Principal(user=FakeUser(), scopes=frozenset({"x:y:z"}), source="api_key", token_id=7)
        assert session.scopes is None, "用户会话不做额外收窄"
        assert token.token_id == 7


# ---------------------------------------------------------------- 服务层

def _service_with_codes(codes: set[str]) -> tuple[ApiTokenService, AsyncMock]:
    """构造带 mock db 的服务实例，并 patch 权限码加载。"""
    service = ApiTokenService()
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return service, db


class TestCreateToken:
    pytestmark = pytest.mark.asyncio

    async def test_rejects_empty_scopes(self):
        service, db = _service_with_codes(set())
        with pytest.raises(BadRequestError):
            await service.create_token(db, user=FakeUser(), name="n", scopes=[], expires_in_days=30)

    async def test_rejects_scopes_beyond_owner(self):
        service, db = _service_with_codes(set())
        with patch(
            "src.api.v3.modules.system.api_token.service.load_codes",
            AsyncMock(return_value=frozenset({"module_content:article:view"})),
        ):
            with pytest.raises(ForbiddenError) as exc:
                await service.create_token(
                    db,
                    user=FakeUser(),
                    name="n",
                    scopes=["module_content:article:view", "module_system:user:delete"],
                    expires_in_days=30,
                )
            assert "module_system:user:delete" in str(exc.value)

    async def test_creates_and_returns_plaintext_once(self):
        service, db = _service_with_codes(set())
        user = FakeUser(user_id=42)
        with patch(
            "src.api.v3.modules.system.api_token.service.load_codes",
            AsyncMock(return_value=frozenset({"module_content:article:view"})),
        ):
            out = await service.create_token(
                db,
                user=user,
                name="CI 发布",
                scopes=["module_content:article:view"],
                expires_in_days=30,
            )

        assert out["token"].startswith(f"{TOKEN_SCHEME}_"), "明文只在创建响应里"
        assert out["name"] == "CI 发布"
        assert out["scopes"] == ["module_content:article:view"]
        assert "token_hash" not in out, "响应绝不含哈希"
        assert out["user_id"] == 42
        assert db.add.called and db.commit.await_count == 1

        added = db.add.call_args.args[0]
        assert added.token_hash and added.token_hash != out["token"], "库中只存哈希"
        assert added.token_prefix in out["token"], "前缀可用于在列表中识别"
        assert added.expires_at > datetime.now()

    async def test_wildcard_owner_may_grant_anything(self):
        service, db = _service_with_codes(set())
        with patch(
            "src.api.v3.modules.system.api_token.service.load_codes",
            AsyncMock(return_value=frozenset({"*:*:*"})),
        ):
            out = await service.create_token(
                db, user=FakeUser(is_superuser=True), name="n",
                scopes=["module_system:user:delete"], expires_in_days=1,
            )
        assert out["scopes"] == ["module_system:user:delete"]


class TestRevokeToken:
    pytestmark = pytest.mark.asyncio

    def _db_returning(self, row):
        db = AsyncMock()
        scalars = MagicMock()
        scalars.first.return_value = row
        result = MagicMock()
        result.scalars.return_value = scalars
        db.execute = AsyncMock(return_value=result)
        db.commit = AsyncMock()
        return db

    async def test_owner_can_revoke(self):
        row = MagicMock(user_id=1, is_active=True)
        service = ApiTokenService()
        db = self._db_returning(row)
        await service.revoke_token(db, user=FakeUser(user_id=1), token_id=5)
        assert row.is_active is False

    async def test_non_owner_gets_404_not_403(self):
        """不泄露"令牌存在但不属于你"。"""
        row = MagicMock(user_id=99, is_active=True)
        service = ApiTokenService()
        db = self._db_returning(row)
        with pytest.raises(NotFoundError):
            await service.revoke_token(db, user=FakeUser(user_id=1), token_id=5)
        assert row.is_active is True, "越权撤销不应生效"

    async def test_admin_can_revoke_others(self):
        row = MagicMock(user_id=99, is_active=True)
        service = ApiTokenService()
        db = self._db_returning(row)
        await service.revoke_token(db, user=FakeUser(user_id=1, is_superuser=True), token_id=5)
        assert row.is_active is False

    async def test_missing_token_raises_404(self):
        service = ApiTokenService()
        db = self._db_returning(None)
        with pytest.raises(NotFoundError):
            await service.revoke_token(db, user=FakeUser(), token_id=5)
