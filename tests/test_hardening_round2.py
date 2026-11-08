# -*- coding: utf-8 -*-
"""本轮审计新增的三处收紧：公开配置、匿名表单、OAuth 邮箱关联。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestPublicSettingsGuard:
    pytestmark = pytest.mark.asyncio

    async def test_sensitive_key_cannot_be_public(self):
        from src.api.v3.core.exceptions import BadRequestError
        from src.api.v3.modules.system.setting.service import setting_service

        for key in ("smtp.password", "site.api_key", "oauth.client_secret", "db.dsn"):
            with pytest.raises(BadRequestError):
                await setting_service.upsert(AsyncMock(), key, value="x", is_public=True)

    async def test_normal_public_key_is_allowed(self):
        from src.api.v3.modules.system.setting import service as setting_module

        row = MagicMock()
        row.setting_key = "site.title"
        row.setting_value = "FastBlog"
        row.setting_type = "string"
        row.description = None
        row.is_public = True

        with patch.object(setting_module.setting_crud, "get_by", AsyncMock(return_value=None)), \
                patch.object(setting_module.setting_crud, "create", AsyncMock(return_value=row)):
            result = await setting_module.setting_service.upsert(
                AsyncMock(), "site.title", value="FastBlog", is_public=True
            )
        assert result["setting_key"] == "site.title"


class TestFormPayloadBounds:
    def test_too_many_fields_rejected(self):
        from src.api.v3.modules.marketing.form.schema import FormPublicSubmitRequest

        with pytest.raises(ValueError):
            FormPublicSubmitRequest(data={f"k{i}": "v" for i in range(60)})

    def test_oversize_value_rejected(self):
        from src.api.v3.modules.marketing.form.schema import FormPublicSubmitRequest

        with pytest.raises(ValueError):
            FormPublicSubmitRequest(data={"message": "x" * 6000})

    def test_normal_payload_accepted(self):
        from src.api.v3.modules.marketing.form.schema import FormPublicSubmitRequest

        payload = FormPublicSubmitRequest(data={"name": "张三", "message": "你好"})
        assert payload.data["name"] == "张三"


class TestOAuthEmailLinking:
    pytestmark = pytest.mark.asyncio

    def _service(self, existing_user):
        from src.api.v3.modules.system.oauth.service import OAuthService

        svc = OAuthService()
        db = AsyncMock()
        db.scalar = AsyncMock(return_value=existing_user)
        return svc, db

    async def test_unverified_email_cannot_hijack_existing_account(self):
        from src.api.v3.core.exceptions import BadRequestError

        svc, db = self._service(MagicMock(id=1))
        with pytest.raises(BadRequestError, match="该邮箱已绑定"):
            await svc._resolve_user(
                db, {"email": "victim@example.com", "email_verified": False}, "github", None
            )

    async def test_verified_email_links_to_existing_account(self):
        existing = MagicMock(id=7)
        svc, db = self._service(existing)
        user, created = await svc._resolve_user(
            db, {"email": "owner@example.com", "email_verified": True}, "google", None
        )
        assert user is existing and created is False

    def test_github_profile_email_is_not_trusted(self):
        from src.api.v3.modules.system.oauth.service import normalize_user_info

        info = normalize_user_info("github", {"id": 1, "login": "u", "email": "evil@x.com"})
        assert info["email_verified"] is False

    def test_google_email_verification_flag_is_kept(self):
        from src.api.v3.modules.system.oauth.service import normalize_user_info

        info = normalize_user_info(
            "google", {"sub": "1", "email": "a@b.com", "email_verified": True}
        )
        assert info["email_verified"] is True
