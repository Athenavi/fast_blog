"""integration 模块业务逻辑：SSO Provider / LDAP 配置（凭据脱敏）"""

from datetime import datetime

from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.system.integration.crud import ldap_config_crud, sso_provider_crud
from src.api.v3.modules.system.integration.schema import (
    LDAPConfigCreate,
    LDAPConfigOut,
    LDAPConfigUpdate,
    SSOProviderCreate,
    SSOProviderOut,
    SSOProviderUpdate,
)


def _sso_out(row) -> dict:
    data = SSOProviderOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["has_client_secret"] = bool(getattr(row, "client_secret", None))
    return data


def _ldap_out(row) -> dict:
    data = LDAPConfigOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["has_bind_password"] = bool(getattr(row, "bind_password", None))
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


integration_service = IntegrationService()
