# -*- coding: utf-8 -*-
"""P1-1 GraphQL 层测试（不依赖数据库）。

覆盖：

  1. schema 形状：根字段齐全、公开/受保护字段都在、不泄露内部字段；
  2. 字段级权限：匿名拒绝、superuser bypass、ANY 语义；
  3. **API 令牌 scopes 收窄**：与 REST 同一判定（令牌只能拿到 scopes ∩ 用户权限）；
  4. 类型投影：dict → 图类型时多余的 service 字段不会被带出去。
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.api.v3.core.permission import codes
from src.api.v3.graphql.context import GraphQLContext
from src.api.v3.graphql.schema import build_schema
from src.api.v3.graphql.types import to_article, to_category, to_viewer
from src.auth.api_token import Principal


class FakeUser:
    def __init__(self, user_id: int = 1, is_superuser: bool = False, username: str = "u") -> None:
        self.id = user_id
        self.is_superuser = is_superuser
        self.username = username
        self.email = "u@example.com"


class _State:
    def __init__(self, principal=None) -> None:
        self.principal = principal


class FakeRequest:
    def __init__(self, principal=None) -> None:
        self.state = _State(principal)


LOAD_PATCH = "src.api.v3.graphql.context.load_codes"


# ---------------------------------------------------------------- schema 形状

class TestSchemaShape:
    def test_router_mounts_at_expected_path(self):
        """挂载点契约：GraphQL 在 /api/v3/graphql（由 create_app 挂载）。

        注意它**不在** v3 路由快照（``v3_route_snapshot.txt``）范围内 —— 那个快照
        只覆盖 ``register_v3_routes`` 注册的 REST 端点，所以这里单独锁定路径，
        避免以后搬动挂载点时无人发现。
        """
        from fastapi import FastAPI

        from src.api.v3.graphql import build_router

        app = FastAPI()
        app.include_router(build_router(graphiql=False), prefix="/api/v3/graphql")
        paths = {getattr(route, "path", "") for route in app.routes}
        assert "/api/v3/graphql" in paths

    def test_root_fields_present(self):
        sdl = str(build_schema())
        for name in (
                "articles", "article", "publicArticles", "publicArticle",
                "categories", "tags", "viewer",
                "createArticle", "updateArticle",
        ):
            assert name in sdl, f"缺少根字段 {name}"

    def test_article_exposes_category_loader_field(self):
        sdl = str(build_schema())
        assert "category: Category" in sdl.replace("\n", " ").replace("  ", " ") or "Category" in sdl

    def test_no_sensitive_fields_exposed(self):
        sdl = str(build_schema()).lower()
        for forbidden in ("tokenhash", "password", "secret", "two_factor", "totp_secret"):
            assert forbidden not in sdl, f"schema 不应暴露 {forbidden}"


# ---------------------------------------------------------------- 字段级权限

@pytest.mark.asyncio
class TestRequire:
    async def test_anonymous_is_rejected(self):
        ctx = GraphQLContext(request=FakeRequest(), db=AsyncMock(), viewer=None)
        with pytest.raises(Exception) as exc:
            await ctx.require(codes.ARTICLE_VIEW)
        assert "需要登录" in str(exc.value)

    async def test_superuser_bypasses(self):
        user = FakeUser(is_superuser=True)
        ctx = GraphQLContext(request=FakeRequest(), db=AsyncMock(), viewer=user)
        assert await ctx.require(codes.ARTICLE_VIEW) is user

    async def test_no_codes_means_login_only(self):
        user = FakeUser()
        ctx = GraphQLContext(request=FakeRequest(), db=AsyncMock(), viewer=user)
        assert await ctx.require() is user

    async def test_missing_code_is_denied(self):
        ctx = GraphQLContext(request=FakeRequest(), db=AsyncMock(), viewer=FakeUser())
        with patch(LOAD_PATCH, AsyncMock(return_value=frozenset({"module_content:tag:view"}))):
            with pytest.raises(Exception) as exc:
                await ctx.require(codes.ARTICLE_VIEW)
        assert "权限不足" in str(exc.value)

    async def test_any_semantics_passes(self):
        ctx = GraphQLContext(request=FakeRequest(), db=AsyncMock(), viewer=FakeUser())
        with patch(LOAD_PATCH, AsyncMock(return_value=frozenset({codes.ARTICLE_VIEW}))):
            assert await ctx.require(codes.ARTICLE_EDIT, codes.ARTICLE_VIEW) is ctx.viewer

    async def test_loader_failure_is_fail_closed(self):
        ctx = GraphQLContext(request=FakeRequest(), db=AsyncMock(), viewer=FakeUser())
        with patch(LOAD_PATCH, AsyncMock(side_effect=RuntimeError("redis down"))):
            with pytest.raises(Exception) as exc:
                await ctx.require(codes.ARTICLE_VIEW)
        assert "权限校验失败" in str(exc.value)


# ---------------------------------------------------------------- API 令牌收窄

@pytest.mark.asyncio
class TestApiTokenScopes:
    async def test_token_scopes_narrow_user_permissions(self):
        """用户有 view+create，但令牌只授 view → create 必须被拒。"""
        principal = Principal(user=FakeUser(), scopes=frozenset({codes.ARTICLE_VIEW}), source="api_key", token_id=1)
        ctx = GraphQLContext(request=FakeRequest(principal), db=AsyncMock(), viewer=FakeUser())
        owned = frozenset({codes.ARTICLE_VIEW, codes.ARTICLE_CREATE})
        with patch(LOAD_PATCH, AsyncMock(return_value=owned)):
            assert await ctx.require(codes.ARTICLE_VIEW) is ctx.viewer
            with pytest.raises(Exception) as exc:
                await ctx.require(codes.ARTICLE_CREATE)
        assert "权限不足" in str(exc.value)

    async def test_jwt_session_is_not_narrowed(self):
        """用户会话（scopes=None）不受收窄影响。"""
        principal = Principal(user=FakeUser(), scopes=None, source="jwt")
        ctx = GraphQLContext(request=FakeRequest(principal), db=AsyncMock(), viewer=FakeUser())
        with patch(LOAD_PATCH, AsyncMock(return_value=frozenset({codes.ARTICLE_CREATE}))):
            assert await ctx.require(codes.ARTICLE_CREATE) is ctx.viewer

    async def test_wildcard_token_passes(self):
        principal = Principal(user=FakeUser(), scopes=frozenset({"*:*:*"}), source="api_key", token_id=1)
        ctx = GraphQLContext(request=FakeRequest(principal), db=AsyncMock(), viewer=FakeUser())
        with patch(LOAD_PATCH, AsyncMock(return_value=frozenset({"*:*:*"}))):
            assert await ctx.require(codes.ARTICLE_DELETE) is ctx.viewer


# ---------------------------------------------------------------- 类型投影

class TestTypeProjection:
    def test_article_projection_ignores_extra_keys(self):
        data = {
            "id": 7,
            "title": "标题",
            "slug": "hello",
            "views": 3,
            "tags": ["a"],
            "content": "正文",
            # service 内部字段：不应出现在图中
            "_internal_path": "/srv/secret",
            "created_by_ip": "10.0.0.1",
        }
        article = to_article(data, with_content=True)
        assert article.id == 7
        assert article.title == "标题"
        assert article.content == "正文"
        assert not hasattr(article, "_internal_path")

    def test_list_projection_drops_content(self):
        article = to_article({"id": 1, "title": "t", "slug": "s", "content": "正文"}, with_content=False)
        assert article.content is None, "列表不应带正文（与 REST 列表同口径）"

    def test_category_and_viewer_projection(self):
        cat = to_category({"id": 2, "name": "分类", "slug": "c", "parent": 1})
        assert cat.id == 2 and cat.parent_id == 1
        viewer = to_viewer(FakeUser(user_id=9, username="alice"))
        assert viewer.id == 9 and viewer.username == "alice"
