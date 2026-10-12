"""api_token 模块的请求 / 响应模型。

安全约定（与 `src/auth/api_token.py` 一致）：

  - 响应**永不包含** ``token_hash``；
  - 明文 ``token`` 只在**创建响应**里出现一次，之后无法再获取。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class ApiTokenCreate(SchemaBase):
    """签发请求。

    ``scopes`` 必填且不能为空：令牌权限 = ``scopes ∩ 归属用户当前权限``，
    必须显式声明用途范围，避免"没写就拿到全部权限"的误解。
    """

    name: str = Field(min_length=1, max_length=100, description="用途备注（如「CI 发布」「官网前端」）")
    scopes: List[str] = Field(
        min_length=1,
        description="权限码子集，必须是归属用户当前权限码的子集；越权会被拒绝（400）",
    )
    expires_in_days: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="有效天数（默认 90 天；避免长期凭证）",
    )


class ApiTokenOut(SchemaBase):
    """列表 / 详情输出（不含 hash，不含明文）"""

    id: int
    name: str
    token_prefix: str
    scopes: List[str]
    user_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool
    created_at: Optional[datetime] = None


class ApiTokenCreated(ApiTokenOut):
    """创建响应：**多一个 ``token`` 字段（明文），仅此一次**"""

    token: str = Field(description="明文令牌：仅本次返回，请立即保存；服务端只存哈希")
