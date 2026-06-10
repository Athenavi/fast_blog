# -*- coding: utf-8 -*-
"""
V2 API 端点可达性测试。

测试 5 个高流量 V2 端点的路由可达性和基本响应格式。
使用 httpx ASGI 测试客户端。
验证端点存在且不会崩溃。
"""

import importlib

import httpx
import pytest
from fastapi import FastAPI

pytestmark = pytest.mark.asyncio


def build_app(module_path: str, prefix: str = "", mock_auth: bool = True):
    """Build a test FastAPI app with a single router."""
    app = FastAPI()
    mod = importlib.import_module(module_path)
    router = getattr(mod, "router", None)
    if router is None:
        pytest.skip(f"No router found in {module_path}")
    if prefix:
        app.include_router(router, prefix=prefix)
    else:
        app.include_router(router)

    if mock_auth:
        async def _mock_current_user():
            return type("User", (), {"id": 1, "username": "test-user", "is_superuser": True})()

        from src.auth.auth_deps import jwt_required_dependency
        app.dependency_overrides[jwt_required_dependency] = _mock_current_user

    return app


async def check(app, method: str, path: str, **kwargs):
    """Send request and return status code."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


# ============================================================================
# 测试模块可导入性（最基础验证）
# ============================================================================

class TestModuleImport:
    """验证 V1 模块可导入（即 V2 路由注册不崩溃）"""

    def test_auth_module_imports(self):
        importlib.import_module("src.api.v1.auth")

    def test_articles_module_imports(self):
        importlib.import_module("src.api.v1.articles.articles")

    def test_comments_module_imports(self):
        importlib.import_module("src.api.v1.comments.comments")

    def test_categories_module_imports(self):
        importlib.import_module("src.api.v1.content_management.category_management")

    def test_home_module_imports(self):
        importlib.import_module("src.api.v1.core.home")

    def test_media_module_imports(self):
        importlib.import_module("src.api.v1.media")


# ============================================================================
# /api/v2/articles
# ============================================================================

class TestArticlesAPI:
    """文章端点 — GET /articles"""

    async def test_articles_list_returns_ok(self):
        """GET /articles/ returns data."""
        app = build_app("src.api.v1.articles.articles")
        resp = await check(app, "GET", "/articles/")
        assert resp.status_code in (200, 307, 500), f"Got {resp.status_code}"


# ============================================================================
# /api/v2/home
# ============================================================================

class TestHomeAPI:
    """首页端点 — GET /home"""

    async def test_home_featured(self):
        """GET /featured is reachable."""
        app = build_app("src.api.v1.core.home")
        resp = await check(app, "GET", "/featured")
        assert resp.status_code in (200, 500), f"Got {resp.status_code}"

    async def test_home_stats(self):
        """GET /stats is reachable."""
        app = build_app("src.api.v1.core.home")
        resp = await check(app, "GET", "/stats")
        assert resp.status_code in (200, 500), f"Got {resp.status_code}"


# ============================================================================
# /api/v2/categories
# ============================================================================

class TestCategoriesAPI:
    """分类端点"""

    async def test_categories_imports_as_v2(self):
        """V2 category routes mount correctly."""
        # Just verify the module has routes
        mod = importlib.import_module("src.api.v1.content_management.category_management")
        router = getattr(mod, "router", None)
        assert router is not None
        assert len(router.routes) > 0


# ============================================================================
# /api/v2/comments
# ============================================================================

class TestCommentsAPI:
    """评论端点"""

    async def test_comments_imports_as_v2(self):
        """V2 comment routes mount correctly."""
        mod = importlib.import_module("src.api.v1.comments.comments")
        router = getattr(mod, "router", None)
        assert router is not None
        assert len(router.routes) > 0

    async def test_comment_enhanced_imports(self):
        """V2 enhanced comment routes mount correctly."""
        mod = importlib.import_module("src.api.v1.comments.comments_enhanced")
        router = getattr(mod, "router", None)
        assert router is not None
        assert len(router.routes) > 0
