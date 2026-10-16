"""MCP 用户上下文 — 独立模块避免循环导入。

``permission_codes`` 是**真实**的三段权限码集合（REST 侧由
``src/api/v3/core/permission/loader.load_codes`` 得到，205 个码见 ``codes.py``）。

``token_scopes`` 仅在使用 **API Token**（``fbk_<prefix>_<secret>``）接入时非 ``None``，
用于把令牌权限收窄到「``scopes`` ∩ 用户当前权限」—— 与 REST 的 ``AuthControl`` 语义一致：
用户被降权时，令牌同步失效。
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import FrozenSet, Optional


@dataclass
class UserCtx:
    """MCP 请求的用户上下文"""

    id: int
    username: str
    is_superuser: bool
    role: str = "user"
    #: 真实三段权限码（``module_{域}:{模块}:{动作}``）
    permission_codes: FrozenSet[str] = field(default_factory=frozenset)
    #: API Token 的 scopes；``None`` 表示走的是用户会话（不做额外收窄）
    token_scopes: Optional[FrozenSet[str]] = None

    def effective_codes(self) -> FrozenSet[str]:
        """实际生效的权限码。

        - 用户会话：就是 ``permission_codes``；
        - API Token：``permission_codes ∩ token_scopes``（令牌永远不能超出用户当前权限）。
        """
        codes = frozenset(self.permission_codes)
        if self.token_scopes is None:
            return codes
        return codes & frozenset(self.token_scopes)


_user_ctx: ContextVar[Optional[UserCtx]] = ContextVar("_mcp_user_ctx", default=None)


def set_user_ctx(user: Optional[UserCtx]) -> None:
    """设置在当前请求上下文中执行的用户"""
    _user_ctx.set(user)


def get_user_ctx() -> Optional[UserCtx]:
    """获取当前请求的用户上下文"""
    return _user_ctx.get()


__all__ = ["UserCtx", "get_user_ctx", "set_user_ctx"]
