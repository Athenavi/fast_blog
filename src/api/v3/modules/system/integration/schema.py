"""integration 模块的请求 / 响应模型（凭据脱敏）"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class SSOProviderCreate(SchemaBase):
    provider_type: str = Field(
        max_length=50,
        description=(
            "oauth2/oidc/saml。**当前仅 oauth2/oidc 接入实际登录流程**；"
            "saml 只是登记配置项，断言（Assertion）校验与元数据端点均未实现，"
            "填 saml 不会产生可用的登录入口。"
        ),
    )
    name: str = Field(min_length=1, max_length=100)
    client_id: str = Field(max_length=200)
    client_secret: str = Field(max_length=255)
    authorization_url: Optional[str] = Field(default=None, max_length=500)
    token_url: Optional[str] = Field(default=None, max_length=500)
    userinfo_url: Optional[str] = Field(default=None, max_length=500)
    scope: Optional[str] = Field(default=None, max_length=200)
    redirect_uri: Optional[str] = Field(default=None, max_length=500)
    attribute_mapping: Optional[str] = Field(default=None, description="属性映射 JSON")
    auto_provision_users: bool = False
    default_role: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = True


class SSOProviderUpdate(SchemaBase):
    provider_type: Optional[str] = Field(default=None, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    client_id: Optional[str] = Field(default=None, max_length=200)
    client_secret: Optional[str] = Field(default=None, max_length=255, description="留空保持原值")
    authorization_url: Optional[str] = Field(default=None, max_length=500)
    token_url: Optional[str] = Field(default=None, max_length=500)
    userinfo_url: Optional[str] = Field(default=None, max_length=500)
    scope: Optional[str] = Field(default=None, max_length=200)
    redirect_uri: Optional[str] = Field(default=None, max_length=500)
    attribute_mapping: Optional[str] = None
    auto_provision_users: Optional[bool] = None
    default_role: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None


class SSOProviderOut(SchemaBase):
    id: int
    provider_type: Optional[str] = None
    name: Optional[str] = None
    client_id: Optional[str] = None
    has_client_secret: bool = False
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    scope: Optional[str] = None
    redirect_uri: Optional[str] = None
    attribute_mapping: Optional[str] = None
    auto_provision_users: bool = False
    default_role: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LDAPConfigCreate(SchemaBase):
    server_url: str = Field(max_length=300)
    bind_dn: Optional[str] = Field(default=None, max_length=300)
    bind_password: Optional[str] = Field(default=None, max_length=300)
    base_dn: Optional[str] = Field(default=None, max_length=300)
    user_filter: Optional[str] = Field(default=None, max_length=300)
    username_attribute: Optional[str] = Field(default=None, max_length=100)
    email_attribute: Optional[str] = Field(default=None, max_length=100)
    first_name_attribute: Optional[str] = Field(default=None, max_length=100)
    last_name_attribute: Optional[str] = Field(default=None, max_length=100)
    use_ssl: bool = True
    verify_certificates: bool = True
    auto_sync_users: bool = False
    sync_interval: int = Field(default=3600, ge=60)
    default_role: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = True


class LDAPConfigUpdate(SchemaBase):
    server_url: Optional[str] = Field(default=None, max_length=300)
    bind_dn: Optional[str] = Field(default=None, max_length=300)
    bind_password: Optional[str] = Field(default=None, max_length=300, description="留空保持原值")
    base_dn: Optional[str] = Field(default=None, max_length=300)
    user_filter: Optional[str] = Field(default=None, max_length=300)
    username_attribute: Optional[str] = Field(default=None, max_length=100)
    email_attribute: Optional[str] = Field(default=None, max_length=100)
    first_name_attribute: Optional[str] = Field(default=None, max_length=100)
    last_name_attribute: Optional[str] = Field(default=None, max_length=100)
    use_ssl: Optional[bool] = None
    verify_certificates: Optional[bool] = None
    auto_sync_users: Optional[bool] = None
    sync_interval: Optional[int] = Field(default=None, ge=60)
    default_role: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None


class LDAPConfigOut(SchemaBase):
    id: int
    server_url: Optional[str] = None
    bind_dn: Optional[str] = None
    has_bind_password: bool = False
    base_dn: Optional[str] = None
    user_filter: Optional[str] = None
    username_attribute: Optional[str] = None
    email_attribute: Optional[str] = None
    use_ssl: bool = True
    verify_certificates: bool = True
    auto_sync_users: bool = False
    sync_interval: int = 3600
    default_role: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- SAML 2.0 (SP 侧)


class SAMLConfigCreate(SchemaBase):
    """SAML 2.0 的 SP 侧配置。

    `idp_certificate` 是**验签用的公钥证书**，按本模块惯例只写不读
    （响应里只给 `has_idp_certificate`）；`sp_private_key` 同理。
    """

    entity_id: str = Field(max_length=255, description="本 SP 的 Entity ID")
    acs_url: str = Field(
        max_length=500, description="Assertion Consumer Service URL（IdP 断言回跳到这里）"
    )
    slo_url: Optional[str] = Field(default=None, max_length=500)
    idp_entity_id: str = Field(
        max_length=255, description="IdP 的 Entity ID，用于校验断言里的 Issuer"
    )
    idp_sso_url: Optional[str] = Field(default=None, max_length=500)
    idp_slo_url: Optional[str] = Field(default=None, max_length=500)
    idp_certificate: str = Field(description="IdP X.509 证书（PEM），断言签名用它验证")
    sp_private_key: Optional[str] = Field(
        default=None, description="本 SP 私钥（PEM），仅当需要 SP 签名请求时使用"
    )
    sp_certificate: Optional[str] = Field(default=None, description="本 SP 证书（PEM）")
    attribute_mapping: Optional[str] = Field(
        default=None,
        description='属性映射 JSON，如 {"email": "mail", "username": "uid"}；不填则按常见属性名猜',
    )
    enable_slo: bool = False
    auto_provision_users: bool = Field(
        default=True, description="断言通过但本地无同名用户时，是否自动建号"
    )
    default_role: Optional[str] = Field(default="subscriber", max_length=50)
    is_active: bool = False


class SAMLConfigUpdate(SchemaBase):
    entity_id: Optional[str] = Field(default=None, max_length=255)
    acs_url: Optional[str] = Field(default=None, max_length=500)
    slo_url: Optional[str] = Field(default=None, max_length=500)
    idp_entity_id: Optional[str] = Field(default=None, max_length=255)
    idp_sso_url: Optional[str] = Field(default=None, max_length=500)
    idp_slo_url: Optional[str] = Field(default=None, max_length=500)
    idp_certificate: Optional[str] = Field(default=None, description="留空保持原值")
    sp_private_key: Optional[str] = Field(default=None, description="留空保持原值")
    sp_certificate: Optional[str] = Field(default=None, description="留空保持原值")
    attribute_mapping: Optional[str] = None
    enable_slo: Optional[bool] = None
    auto_provision_users: Optional[bool] = None
    default_role: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None


class SAMLConfigOut(SchemaBase):
    id: int
    entity_id: Optional[str] = None
    acs_url: Optional[str] = None
    slo_url: Optional[str] = None
    idp_entity_id: Optional[str] = None
    idp_sso_url: Optional[str] = None
    idp_slo_url: Optional[str] = None
    attribute_mapping: Optional[str] = None
    enable_slo: bool = False
    auto_provision_users: bool = True
    default_role: Optional[str] = None
    is_active: bool = False
    has_idp_certificate: bool = False
    has_sp_private_key: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
