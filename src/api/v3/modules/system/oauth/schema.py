"""oauth 模块的请求 / 响应模型（令牌字段一律脱敏）"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class ProviderOut(SchemaBase):
    """单个 OAuth 提供方（``configured`` 表示 ``oauth.providers`` 里是否填了 client_id/secret）"""

    key: str
    name: str
    icon: str
    configured: bool = False
    supports_pkce: bool = False


class AuthorizeUrlOut(SchemaBase):
    """授权跳转信息

    ``code_verifier`` 交由调用方（前端）在回调时原样回传（标准 PKCE 做法）；
    仅对支持 PKCE 的提供方（见 ``service.PKCE_PROVIDERS``）返回，其余为 ``None``。
    """

    provider: str
    authorize_url: str
    state: str
    redirect_uri: str
    code_verifier: Optional[str] = None
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None


class CallbackRequest(SchemaBase):
    """回调请求体（POST 形态；GET 回调从 query 读取同名字段）"""

    code: str = Field(min_length=1, max_length=2048, description="厂商返回的授权码")
    state: str = Field(min_length=1, max_length=512, description="授权时下发的 state（防 CSRF）")
    code_verifier: Optional[str] = Field(
        default=None, max_length=128, description="PKCE 校验串（调用方在授权时拿到）"
    )
    remember_me: bool = Field(default=False, description="是否签发 refresh token")


class BindingOut(SchemaBase):
    """本人已绑定的第三方账号（脱敏：只返回是否已存到 token）"""

    id: int
    provider: Optional[str] = None
    provider_user_id: Optional[str] = None
    has_token: bool = False
    token_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CallbackResultOut(SchemaBase):
    """回调结果：登录态 + 绑定信息"""

    provider: str
    user_id: int
    username: Optional[str] = None
    bound: bool = True
    created_user: bool = False
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
