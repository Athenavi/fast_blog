"""social 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class OAuthAccountOut(SchemaBase):
    """令牌字段脱敏：只返回是否已取到 token"""

    id: int
    user_id: Optional[int] = None
    provider: Optional[str] = None
    provider_user_id: Optional[str] = None
    has_token: bool = False
    token_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OAuthAccountQuery(SchemaBase):
    user_id: Optional[int] = None
    provider: Optional[str] = Field(default=None, max_length=50)
