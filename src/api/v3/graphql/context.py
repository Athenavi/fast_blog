"""GraphQL 请求上下文与**字段级权限检查**。

权限语义与 REST 的 ``AuthControl`` **完全一致**（ANY + 通配 + superuser bypass +
API 令牌 scopes 收窄 + fail-closed），并且复用同一组判定函数
（``permission.control.satisfies`` / ``permission.control.token_scopes``），
避免 GraphQL 与 REST 出现两套会各自漂移的权限判断。
"""

from dataclasses import dataclass
from typing import Any, Optional

from strawberry.exceptions import GraphQLError

from src.api.v3.core.permission.constants import WILDCARD_CODES
from src.api.v3.core.permission.control import satisfies, token_scopes
from src.api.v3.core.permission.loader import load_codes


@dataclass
class GraphQLContext:
    request: Any
    db: Any
    viewer: Optional[Any] = None
    principal: Optional[Any] = None
    #: 分类批量加载器（每个请求一个实例；见 graphql/loaders.py）
    category_loader: Optional[Any] = None

    async def require(self, *codes: str) -> Any:
        """校验当前身份是否满足 ``codes``（ANY 语义）；不满足抛 GraphQL 错误。

        不传 ``codes`` 表示"仅需登录"。
        """
        if self.viewer is None:
            raise GraphQLError("需要登录")
        if getattr(self.viewer, "is_superuser", False):
            return self.viewer
        if not codes:
            return self.viewer

        # 收窄判定放在 try 之外：它不是 I/O，出问题应直接暴露，
        # 不能被"加载失败"的 except 伪装成权限不足。
        scopes = token_scopes(self.request)
        try:
            owned = frozenset(await load_codes(self.db, self.viewer.id, request=self.request))
        except Exception as exc:  # noqa: BLE001 - 加载失败一律拒绝（fail-closed）
            raise GraphQLError("权限校验失败") from exc
        if scopes is not None:
            owned = owned & scopes
        if WILDCARD_CODES.intersection(owned):
            return self.viewer
        if not any(satisfies(code, owned) for code in codes):
            raise GraphQLError(f"权限不足：需要 {'/'.join(codes)}")
        return self.viewer


async def get_context(request, db, viewer) -> GraphQLContext:
    """由 FastAPI 依赖组装上下文（见 ``graphql/schema.py`` 的 router 工厂）。"""
    from src.api.v3.graphql.loaders import CategoryLoader

    return GraphQLContext(
        request=request,
        db=db,
        viewer=viewer,
        principal=getattr(getattr(request, "state", None), "principal", None),
        category_loader=CategoryLoader(db),
    )
