"""GraphQL 接入（``/api/v3/graphql``）。

只读查询 + 少量写（文章 create/update），鉴权与权限语义与 REST 完全同源。
"""

from src.api.v3.graphql.schema import build_router, build_schema

__all__ = ["build_router", "build_schema"]
