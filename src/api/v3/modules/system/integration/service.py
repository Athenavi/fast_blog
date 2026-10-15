"""integration 模块业务逻辑：SSO Provider / LDAP / SAML 配置，以及 SAML 断言消费（ACS）。

凭据（`client_secret` / `bind_password` / `idp_certificate` / `sp_private_key`）
一律**只写不读**：响应里只给 `has_*` 布尔位。
"""

import json
import re
import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.integration.crud import (
    ldap_config_crud,
    saml_config_crud,
    sso_provider_crud,
)
from src.api.v3.modules.system.integration.saml import (
    SamlValidationError,
    build_sp_metadata,
    validate_saml_response,
)
from src.api.v3.modules.system.integration.schema import (
    LDAPConfigCreate,
    LDAPConfigOut,
    LDAPConfigUpdate,
    SAMLConfigCreate,
    SAMLConfigOut,
    SAMLConfigUpdate,
    SSOProviderCreate,
    SSOProviderOut,
    SSOProviderUpdate,
)

logger = get_logger("system.integration")


def _sso_out(row) -> dict:
    data = SSOProviderOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["has_client_secret"] = bool(getattr(row, "client_secret", None))
    return data


def _ldap_out(row) -> dict:
    data = LDAPConfigOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["has_bind_password"] = bool(getattr(row, "bind_password", None))
    return data


def _saml_out(row) -> dict:
    data = SAMLConfigOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["has_idp_certificate"] = bool(getattr(row, "idp_certificate", None))
    data["has_sp_private_key"] = bool(getattr(row, "sp_private_key", None))
    return data


class IntegrationService:
    """第三方集成（system 域）"""

    # ------------------------------------------------------------ SSO
    async def list_sso(self, db: AsyncSession) -> list[dict]:
        rows, _ = await sso_provider_crud.list(db, page=1, page_size=100)
        return [_sso_out(r) for r in rows]

    async def create_sso(self, db: AsyncSession, payload: SSOProviderCreate) -> dict:
        row = await sso_provider_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _sso_out(row)

    async def update_sso(self, db: AsyncSession, provider_id: int, payload: SSOProviderUpdate) -> dict:
        row = await sso_provider_crud.get(db, provider_id)
        if row is None:
            raise NotFoundError("SSO 配置不存在")
        data = payload.model_dump(exclude_unset=True)
        if "client_secret" in data and not data["client_secret"]:
            data.pop("client_secret")  # 留空保持原值
        updated = await sso_provider_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _sso_out(updated)

    async def delete_sso(self, db: AsyncSession, provider_id: int) -> None:
        row = await sso_provider_crud.get(db, provider_id)
        if row is None:
            raise NotFoundError("SSO 配置不存在")
        await sso_provider_crud.remove(db, row)

    # ------------------------------------------------------------ LDAP
    async def list_ldap(self, db: AsyncSession) -> list[dict]:
        rows, _ = await ldap_config_crud.list(db, page=1, page_size=100)
        return [_ldap_out(r) for r in rows]

    async def create_ldap(self, db: AsyncSession, payload: LDAPConfigCreate) -> dict:
        row = await ldap_config_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _ldap_out(row)

    async def update_ldap(self, db: AsyncSession, config_id: int, payload: LDAPConfigUpdate) -> dict:
        row = await ldap_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("LDAP 配置不存在")
        data = payload.model_dump(exclude_unset=True)
        if "bind_password" in data and not data["bind_password"]:
            data.pop("bind_password")
        updated = await ldap_config_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _ldap_out(updated)

    async def delete_ldap(self, db: AsyncSession, config_id: int) -> None:
        row = await ldap_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("LDAP 配置不存在")
        await ldap_config_crud.remove(db, row)

    # ------------------------------------------------------------ SAML 2.0
    async def list_saml(self, db: AsyncSession) -> list[dict]:
        rows, _ = await saml_config_crud.list(db, page=1, page_size=100)
        return [_saml_out(r) for r in rows]

    async def create_saml(self, db: AsyncSession, payload: SAMLConfigCreate) -> dict:
        row = await saml_config_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _saml_out(row)

    async def update_saml(
        self, db: AsyncSession, config_id: int, payload: SAMLConfigUpdate
    ) -> dict:
        row = await saml_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("SAML 配置不存在")
        data = payload.model_dump(exclude_unset=True)
        # 凭据留空 = 保持原值（与 SSOProvider 的 client_secret、LDAP 的 bind_password 同一约定）
        for secret in ("idp_certificate", "sp_private_key", "sp_certificate"):
            if secret in data and not data[secret]:
                data.pop(secret)
        updated = await saml_config_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _saml_out(updated)

    async def delete_saml(self, db: AsyncSession, config_id: int) -> None:
        row = await saml_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("SAML 配置不存在")
        await saml_config_crud.remove(db, row)

    async def _require_saml(self, db: AsyncSession, config_id: int):
        row = await saml_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("SAML 配置不存在")
        return row

    async def saml_sp_metadata(self, db: AsyncSession, config_id: int) -> bytes:
        """生成 SP 元数据（EntityDescriptor），交给 IdP 侧登记。"""
        row = await self._require_saml(db, config_id)
        if not row.entity_id or not row.acs_url:
            raise BadRequestError("SAML 配置缺少 entity_id 或 acs_url，无法生成元数据")
        return build_sp_metadata(entity_id=row.entity_id, acs_url=row.acs_url)

    async def saml_acs(
        self,
        db: AsyncSession,
        config_id: int,
        raw_response: str,
        *,
        ip: str = "unknown",
        user_agent: str = "",
    ) -> dict:
        """ACS：校验断言 → 定位/新建用户 → 签发登录态。

        校验失败一律转成 `BadRequestError("SAML 断言校验未通过")`，**不回显**是哪一步
        失败 —— 那等于告诉攻击者"差哪一点就过了"。细节只进服务端日志。
        """
        row = await self._require_saml(db, config_id)
        if not row.is_active:
            raise BadRequestError("该 SAML 配置未启用")
        if not row.entity_id:
            raise BadRequestError("SAML 配置缺少 SP entity_id")
        if not row.idp_certificate:
            raise BadRequestError("SAML 配置缺少 IdP 证书，无法验签")

        mapping: dict[str, Any] = {}
        if row.attribute_mapping:
            try:
                parsed = json.loads(row.attribute_mapping)
            except ValueError as exc:
                raise BadRequestError("SAML 配置的 attribute_mapping 不是合法 JSON") from exc
            if not isinstance(parsed, dict):
                raise BadRequestError("SAML 配置的 attribute_mapping 必须是 JSON 对象")
            mapping = parsed

        try:
            identity = await validate_saml_response(
                raw_response,
                db=db,
                idp_cert_pem=row.idp_certificate,
                idp_entity_id=row.idp_entity_id or "",
                sp_entity_id=row.entity_id,
                attribute_mapping=mapping,
            )
        except SamlValidationError as exc:
            logger.warning("SAML 断言校验失败 config=%s: %s", config_id, exc)
            raise BadRequestError("SAML 断言校验未通过") from exc

        user, created = await self._resolve_saml_user(db, row, identity)

        # 签发登录态：与账号密码登录、OAuth 登录复用同一条路径
        from src.api.v3.modules.system.auth.service import auth_service

        tokens = await auth_service.grant_tokens(db, user, ip=ip, user_agent=user_agent)

        return {
            "tokens": tokens,
            "identity": {
                "name_id": identity.name_id,
                "assertion_id": identity.assertion_id,
                "issuer": identity.issuer,
                "email": identity.email,
                "username": identity.username,
                "created_user": created,
            },
        }

    async def _resolve_saml_user(
        self, db: AsyncSession, row, identity
    ) -> tuple[Any, bool]:
        """按「同邮箱 → 同用户名 → 新建」定位本地用户，返回 `(user, created)`。

        与 oauth 的 `_resolve_user` 策略一致；没有强行复用是因为那是 `OAuthService`
        的私有方法，跨模块调用会把两个域的耦合做死，而这段逻辑不到 30 行。
        """
        email = (identity.email or "").strip().lower()
        if email:
            existing = await db.scalar(
                select(User).where(func.lower(User.email) == email).limit(1)
            )
            if existing is not None:
                return existing, False

        username = (identity.username or identity.name_id or "").strip()
        if username:
            existing = await db.scalar(
                select(User).where(User.username == username).limit(1)
            )
            if existing is not None:
                return existing, False

        if not row.auto_provision_users:
            # 给管理员一个能照着做的提示，而不是含糊的 401
            raise BadRequestError(
                "该 SAML 身份在本地没有对应账号，且未开启自动建号"
                "（请在配置里打开 auto_provision_users，或先手动建号）"
            )

        seed = re.sub(r"[^\w.\-]", "", username or email.split("@")[0] or "saml_user")[:24]
        candidate = seed or "saml_user"
        for _ in range(20):
            taken = await db.scalar(
                select(User.id).where(User.username == candidate).limit(1)
            )
            if taken is None:
                break
            candidate = f"{seed or 'saml_user'}_{secrets.token_hex(2)}"

        now = datetime.now()
        user = User(
            username=candidate,
            email=email or None,
            password=None,  # SAML 账号无本地密码，只能经 IdP 登录
            locale="zh_CN",
            is_active=True,
            date_joined=now,
        )
        db.add(user)
        await db.flush()
        logger.info(
            "SAML 新建本地账号 config=%s user=%s username=%s", row.id, user.id, candidate
        )
        return user, True


integration_service = IntegrationService()
