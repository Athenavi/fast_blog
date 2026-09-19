"""integration 模块路由（T5-11 批次 3：自 astro `admin/integrations` 能力域新建）

::

    GET    /api/v3/system/integration/sso                SSO Provider 列表
    POST   /api/v3/system/integration/sso                新建 SSO
    PUT    /api/v3/system/integration/sso/{provider_id}  更新 SSO（client_secret 留空保持原值）
    DELETE /api/v3/system/integration/sso/{provider_id}  删除 SSO
    GET    /api/v3/system/integration/ldap               LDAP 列表
    POST   /api/v3/system/integration/ldap               新建 LDAP
    PUT    /api/v3/system/integration/ldap/{config_id}   更新 LDAP（bind_password 留空保持原值）
    DELETE /api/v3/system/integration/ldap/{config_id}   删除 LDAP

权限码：``module_system:integration:view/create/edit/delete``。
凭据（client_secret / bind_password）只写不读，响应仅含 has_* 布尔位。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.integration.schema import (
    LDAPConfigCreate,
    LDAPConfigUpdate,
    SSOProviderCreate,
    SSOProviderUpdate,
)
from src.api.v3.modules.system.integration.service import integration_service

router = APIRouter(prefix="/integration", tags=["system-integration"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- SSO
@router.get("/sso", response_model=ResponseModel, summary="SSO Provider 列表")
async def list_sso(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_VIEW),
) -> dict:
    return resp.success(await integration_service.list_sso(db))


@router.post("/sso", response_model=ResponseModel, summary="新建 SSO Provider")
async def create_sso(
    payload: SSOProviderCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_CREATE),
) -> dict:
    return resp.success(await integration_service.create_sso(db, payload), msg="已创建")


@router.put("/sso/{provider_id}", response_model=ResponseModel, summary="更新 SSO Provider")
async def update_sso(
    provider_id: int,
    payload: SSOProviderUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_EDIT),
) -> dict:
    return resp.success(await integration_service.update_sso(db, provider_id, payload), msg="已保存")


@router.delete("/sso/{provider_id}", response_model=ResponseModel, summary="删除 SSO Provider")
async def delete_sso(
    provider_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_DELETE),
) -> dict:
    await integration_service.delete_sso(db, provider_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- LDAP
@router.get("/ldap", response_model=ResponseModel, summary="LDAP 列表")
async def list_ldap(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_VIEW),
) -> dict:
    return resp.success(await integration_service.list_ldap(db))


@router.post("/ldap", response_model=ResponseModel, summary="新建 LDAP")
async def create_ldap(
    payload: LDAPConfigCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_CREATE),
) -> dict:
    return resp.success(await integration_service.create_ldap(db, payload), msg="已创建")


@router.put("/ldap/{config_id}", response_model=ResponseModel, summary="更新 LDAP")
async def update_ldap(
    config_id: int,
    payload: LDAPConfigUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_EDIT),
) -> dict:
    return resp.success(await integration_service.update_ldap(db, config_id, payload), msg="已保存")


@router.delete("/ldap/{config_id}", response_model=ResponseModel, summary="删除 LDAP")
async def delete_ldap(
    config_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_DELETE),
) -> dict:
    await integration_service.delete_ldap(db, config_id)
    return resp.success(None, msg="已删除")
