# -*- coding: utf-8 -*-
"""文章修订历史的**接线**测试

``revision_service`` 有 475 行、7 个方法（hash/保存/列表/详情/回滚/对比/删除），
实现是完整的，但此前**全仓只有 `article_manager/__init__.py` 的 re-export、
没有任何业务调用** —— 也就是说"修订历史"这个能力实际上不存在。

这里测的是**接线**，不是那份既有实现（后者不该由本测试负责）：

1. ``update_article`` 保存后必须调用 ``save_article_revision``；
2. ``rollback_revision`` 必须**先保存当前状态**再回滚 —— 否则被回滚掉的版本
   永久丢失，用户无法撤销这次回滚；
3. 四个修订路由已注册。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SAVE_PATH = "src.api.v3.modules.content.article.service.save_article_revision"
_ROLLBACK_PATH = "src.api.v3.modules.content.article.service.rollback_to_revision"


@pytest.mark.unit
class TestRevisionWiring:
    @pytest.mark.asyncio
    async def test_update_article_saves_revision(self):
        """保存文章后必须落一条修订（author_id 取自 scope_user）"""
        from src.api.v3.modules.content.article.crud import article_crud
        from src.api.v3.modules.content.article.schema import ArticleUpdate
        from src.api.v3.modules.content.article.service import ArticleService

        existing = MagicMock()
        existing.status = 0
        existing.user = 7
        scope_user = MagicMock()
        scope_user.id = 99

        svc = ArticleService()
        with patch.object(article_crud, "get", AsyncMock(return_value=existing)), \
            patch.object(article_crud, "update", AsyncMock(return_value=existing)), \
            patch.object(svc, "_invalidate", AsyncMock()), \
            patch.object(svc, "get_article", AsyncMock(return_value={"id": 42})), \
            patch(_SAVE_PATH, AsyncMock(return_value=None)) as mock_save:
            await svc.update_article(
                AsyncMock(), 42, ArticleUpdate(title="New"), scope_user=scope_user
            )

        assert mock_save.await_count == 1, "update_article 必须保存一条修订"
        assert mock_save.await_args.args[2] == 99, "author_id 应取自 scope_user.id"

    @pytest.mark.asyncio
    async def test_rollback_saves_current_state_first(self):
        """回滚前必须先保存当前状态 —— 否则这次回滚无法被撤销"""
        from src.api.v3.modules.content.article.service import ArticleService

        calls: list = []

        async def fake_save(db, article_id, author_id, summary=None):
            calls.append("save")

        async def fake_rollback(db, article_id, revision_id, author_id):
            calls.append("rollback")
            return True

        svc = ArticleService()
        with patch(_SAVE_PATH, fake_save), \
            patch(_ROLLBACK_PATH, fake_rollback), \
            patch.object(svc, "_invalidate", AsyncMock()), \
            patch.object(svc, "get_article", AsyncMock(return_value={"id": 42})):
            await svc.rollback_revision(AsyncMock(), 42, 7, author_id=1)

        assert calls == ["save", "rollback"], (
            "回滚顺序必须是先保存当前状态再回滚"
        )

    @pytest.mark.asyncio
    async def test_rollback_failure_raises_not_found(self):
        """目标修订不存在时抛 NotFoundError，而不是静默返回"""
        from src.api.v3.core.exceptions import NotFoundError
        from src.api.v3.modules.content.article.service import ArticleService

        svc = ArticleService()
        with patch(_SAVE_PATH, AsyncMock(return_value=None)), \
            patch(_ROLLBACK_PATH, AsyncMock(return_value=False)):
            with pytest.raises(NotFoundError):
                await svc.rollback_revision(AsyncMock(), 42, 999999, author_id=1)


@pytest.mark.unit
class TestRevisionRoutes:
    def test_revision_routes_registered(self):
        """四个修订路由必须都挂上（compare 是静态路径，需在 {revision_id} 之前）"""
        from src.app import app

        paths = [getattr(route, "path", "") for route in app.routes]
        for expected in (
                "/api/v3/content/article/{article_id}/revisions",
                "/api/v3/content/article/{article_id}/revisions/{revision_id}",
                "/api/v3/content/article/{article_id}/revisions/{revision_id}/rollback",
                "/api/v3/content/article/{article_id}/revisions/compare",
        ):
            assert expected in paths, f"缺少路由 {expected}"

    def test_compare_registered_before_revision_id(self):
        """静态的 /revisions/compare 必须排在 /revisions/{revision_id} 之前

        否则 ``compare`` 会被当成 revision_id 匹配掉（与 /batch/*、/public/* 同一约定）。
        """
        from src.app import app

        paths = [getattr(route, "path", "") for route in app.routes]
        compare_idx = paths.index(
            "/api/v3/content/article/{article_id}/revisions/compare"
        )
        detail_idx = paths.index(
            "/api/v3/content/article/{article_id}/revisions/{revision_id}"
        )
        assert compare_idx < detail_idx, "compare 必须注册在 {revision_id} 之前"
