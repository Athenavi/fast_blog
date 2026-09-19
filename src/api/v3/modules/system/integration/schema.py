"""integration 模块的请求 / 响应模型（凭据脱敏）"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class SSOProviderCreate(SchemaBase):
    provider_type: str = Field(max_length=50, description="oauth2/oidc/saml…")
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
