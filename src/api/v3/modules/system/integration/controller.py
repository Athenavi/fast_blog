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

SAML 2.0（SP 侧，阶段 0 补齐"仅 SAML 未实现"的部分）::

    GET    /api/v3/system/integration/saml               SAML 配置列表
    POST   /api/v3/system/integration/saml               新建 SAML
    PUT    /api/v3/system/integration/saml/{config_id}   更新 SAML（证书/私钥留空保持原值）
    DELETE /api/v3/system/integration/saml/{config_id}   删除 SAML
    GET    /api/v3/system/integration/saml/{config_id}/metadata   SP 元数据（XML，交给 IdP 登记）
    POST   /api/v3/system/integration/saml/{config_id}/acs        IdP 断言回跳（**匿名**）

权限码：``module_system:integration:view/create/edit/delete``。
凭据（client_secret / bind_password / idp_certificate / sp_private_key）只写不读，
响应仅含 has_* 布尔位。

**ACS 是唯一匿名端点**：身份由已验签的断言证明，因此它不挂 ``AuthControl``；
校验失败一律返回同一个错误，不区分签名错/过期/受众不符（避免把校验细节回显出去）。
"""

from fastapi import APIRouter, Form, Request, Response

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.integration.schema import (
    LDAPConfigCreate,
    LDAPConfigUpdate,
    SAMLConfigCreate,
    SAMLConfigUpdate,
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


# ---------------------------------------------------------------- SAML 2.0
@router.get("/saml", response_model=ResponseModel, summary="SAML 配置列表")
async def list_saml(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_VIEW),
) -> dict:
    return resp.success(await integration_service.list_saml(db))


@router.post("/saml", response_model=ResponseModel, summary="新建 SAML 配置")
async def create_saml(
    payload: SAMLConfigCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_CREATE),
) -> dict:
    return resp.success(await integration_service.create_saml(db, payload), msg="已创建")


@router.put("/saml/{config_id}", response_model=ResponseModel, summary="更新 SAML 配置")
async def update_saml(
    config_id: int,
    payload: SAMLConfigUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_EDIT),
) -> dict:
    return resp.success(await integration_service.update_saml(db, config_id, payload), msg="已保存")


@router.delete("/saml/{config_id}", response_model=ResponseModel, summary="删除 SAML 配置")
async def delete_saml(
    config_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_DELETE),
) -> dict:
    await integration_service.delete_saml(db, config_id)
    return resp.success(None, msg="已删除")


@router.get(
    "/saml/{config_id}/metadata",
    summary="SP 元数据（把这份 XML 交给 IdP 登记）",
    response_class=Response,
)
async def saml_metadata(
    config_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_VIEW),
) -> Response:
    xml = await integration_service.saml_sp_metadata(db, config_id)
    return Response(content=xml, media_type="application/samlmetadata+xml")


@router.post("/saml/{config_id}/acs", response_model=ResponseModel, summary="SAML 断言消费（IdP 回调）")
async def saml_acs(
    config_id: int,
    request: Request,
    db: DBSession,
    saml_response: str = Form(..., alias="SAMLResponse"),
) -> dict:
    """IdP 的断言回跳入口（Assertion Consumer Service）。

    **刻意不挂 `AuthControl`**：这个请求来自 IdP，用户此刻还没有本站登录态；
    身份完全由断言本身证明（签名 + 有效期 + 受众 + 重放，见 `integration/saml.py`）。
    任何校验失败都返回同一个 400，不区分原因。
    """
    client_ip = request.client.host if request.client else "unknown"
    result = await integration_service.saml_acs(
        db,
        config_id,
        saml_response,
        ip=client_ip,
        user_agent=request.headers.get("user-agent", ""),
    )
    return resp.success(result, msg="登录成功")
