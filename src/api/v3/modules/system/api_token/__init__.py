"""system/api_token：对外 API 令牌（第三方应用 / CI 接入）

令牌权限 = ``scopes ∩ 归属用户当前权限码``；明文只在创建响应里返回一次。
"""

from src.api.v3.modules.system.api_token.service import ApiTokenService

__all__ = ["ApiTokenService"]
