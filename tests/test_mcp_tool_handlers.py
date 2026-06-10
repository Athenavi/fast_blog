# -*- coding: utf-8 -*-
"""
MCP 工具 handler 测试（拆分后版本）。

工具处理器已从 MCPServer 类方法拆分为 tools/ 下的独立异步函数。
测试调用函数本身，而非 mcp_server 方法。
"""
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp.tools import content as content_tools
from src.mcp.tools import analytics as analytics_tools
from src.mcp.tools import media as media_tools

pytestmark = pytest.mark.asyncio


# ============================================================================
# 辅助函数
# ============================================================================

def _mock_db_session(rows=None, scalar=None):
    session = AsyncMock()
    execute_result = MagicMock()
    if rows is not None:
        execute_result.scalars.return_value.all.return_value = rows
    if scalar is not None:
        execute_result.scalar_one_or_none.return_value = scalar
        execute_result.scalar.return_value = scalar
    session.execute.return_value = execute_result
    # Make session.scalar() work directly (new optimized code uses db.scalar)
    session.scalar = AsyncMock(return_value=scalar)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


def _mock_article(**kwargs):
    a = MagicMock()
    a.id = kwargs.get("id", 1)
    a.title = kwargs.get("title", "Test Article")
    a.slug = kwargs.get("slug", "test-article")
    a.status = kwargs.get("status", 1)
    a.views = kwargs.get("views", 100)
    a.likes = kwargs.get("likes", 10)
    a.created_at = kwargs.get("created_at", datetime.datetime(2026, 6, 1, 0, 0, 0))
    return a


def _mock_comment(**kwargs):
    c = MagicMock()
    c.id = kwargs.get("id", 1)
    c.article_id = kwargs.get("article_id", 1)
    c.content = kwargs.get("content", "Nice post!")
    c.author_name = kwargs.get("author_name", "Tester")
    c.is_approved = kwargs.get("is_approved", True)
    c.likes = kwargs.get("likes", 0)
    c.user_id = kwargs.get("user_id", 1)
    c.created_at = kwargs.get("created_at", datetime.datetime(2026, 6, 1, 0, 0, 0))
    c.updated_at = kwargs.get("updated_at", datetime.datetime(2026, 6, 1, 0, 0, 0))
    return c


def _mock_media(**kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", 1)
    m.filename = kwargs.get("filename", "photo.jpg")
    m.original_filename = kwargs.get("original_filename", "photo.jpg")
    m.mime_type = kwargs.get("mime_type", "image/jpeg")
    m.file_size = kwargs.get("file_size", 102400)
    m.file_url = kwargs.get("file_url", "/media/photo.jpg")
    m.alt_text = kwargs.get("alt_text", "")
    m.category = kwargs.get("category", "")
    m.created_at = kwargs.get("created_at", datetime.datetime(2026, 6, 1, 0, 0, 0))
    m.updated_at = kwargs.get("updated_at", datetime.datetime(2026, 6, 1, 0, 0, 0))
    return m


# ============================================================================
# 评论工具
# ============================================================================

class TestCommentTools:
    PATCH_TARGET = "src.mcp.tools.content.get_async_session_context"

    @patch(PATCH_TARGET)
    async def test_list_comments(self, mock_ctx):
        comments = [_mock_comment(id=1, content="First"), _mock_comment(id=2, content="Second")]
        session = _mock_db_session(rows=comments)
        mock_ctx.return_value.__aenter__.return_value = session
        result = await content_tools.list_comments({"status": "pending", "limit": 20})
        assert result["success"] is True
        assert len(result["comments"]) == 2
        assert result["comments"][0]["content"] == "First"

    @patch(PATCH_TARGET)
    async def test_approve_comment(self, mock_ctx):
        comment = _mock_comment(id=42, is_approved=False)
        session = _mock_db_session(scalar=comment)
        mock_ctx.return_value.__aenter__.return_value = session
        result = await content_tools.approve_comment({"comment_id": 42})
        assert result["success"] is True
        assert comment.is_approved is True
        session.commit.assert_called_once()

    @patch(PATCH_TARGET)
    async def test_reject_comment(self, mock_ctx):
        comment = _mock_comment(id=7, is_approved=True)
        session = _mock_db_session(scalar=comment)
        mock_ctx.return_value.__aenter__.return_value = session
        result = await content_tools.reject_comment({"comment_id": 7})
        assert result["success"] is True
        assert comment.is_approved is False


# ============================================================================
# 分析工具
# ============================================================================

class TestAnalyticsTools:
    PATCH_TARGET = "src.mcp.tools.analytics.get_async_session_context"

    @patch(PATCH_TARGET)
    async def test_get_analytics(self, mock_ctx):
        session = _mock_db_session(scalar=42)
        mock_ctx.return_value.__aenter__.return_value = session
        result = await analytics_tools.get_analytics({})
        assert result["success"] is True
        assert result["data"]["articles"]["published"] == 42
        assert result["data"]["users"] == 42

    @patch(PATCH_TARGET)
    async def test_get_trending_articles(self, mock_ctx):
        articles = [_mock_article(id=1, title="Top 1", views=500)]
        session = _mock_db_session(rows=articles, scalar=None)
        mock_ctx.return_value.__aenter__.return_value = session
        result = await analytics_tools.get_trending_articles({"limit": 5, "days": 7})
        assert result["success"] is True
        assert len(result["articles"]) == 1
        assert result["articles"][0]["title"] == "Top 1"


# ============================================================================
# 媒体工具
# ============================================================================

class TestMediaTools:
    PATCH_TARGET = "src.mcp.tools.media.get_async_session_context"

    @patch(PATCH_TARGET)
    async def test_list_media(self, mock_ctx):
        media = [_mock_media(id=1, filename="img1.jpg"), _mock_media(id=2, filename="vid.mp4", mime_type="video/mp4")]
        session = _mock_db_session(rows=media)
        mock_ctx.return_value.__aenter__.return_value = session
        result = await media_tools.list_media({"limit": 10})
        assert result["success"] is True
        assert len(result["media"]) == 2

    @patch(PATCH_TARGET)
    async def test_list_media_with_type_filter(self, mock_ctx):
        session = _mock_db_session(rows=[])
        mock_ctx.return_value.__aenter__.return_value = session
        result = await media_tools.list_media({"media_type": "image", "limit": 5})
        assert result["success"] is True
        call_args = session.execute.call_args[0][0]
        assert "mime_type" in str(call_args)

    @patch(PATCH_TARGET)
    async def test_delete_media(self, mock_ctx):
        media = _mock_media(id=5)
        session = _mock_db_session(scalar=media)
        mock_ctx.return_value.__aenter__.return_value = session
        result = await media_tools.delete_media({"media_id": 5})
        assert result["success"] is True
        session.delete.assert_called_once_with(media)


# ============================================================================
# 分类/标签工具
# ============================================================================

class TestCategoryTagTools:
    PATCH_TARGET = "src.mcp.tools.content.get_async_session_context"

    @patch(PATCH_TARGET)
    async def test_update_category(self, mock_ctx):
        cat = MagicMock()
        cat.id = 3
        cat.name = "Old Name"
        session = _mock_db_session(scalar=cat)
        mock_ctx.return_value.__aenter__.return_value = session
        result = await content_tools.update_category({"category_id": 3, "name": "New Name"})
        assert result["success"] is True
        assert cat.name == "New Name"
        session.commit.assert_called_once()

    @patch(PATCH_TARGET)
    async def test_delete_category(self, mock_ctx):
        cat = MagicMock()
        cat.id = 7
        session = _mock_db_session(scalar=cat)
        mock_ctx.return_value.__aenter__.return_value = session
        result = await content_tools.delete_category({"category_id": 7})
        assert result["success"] is True
        session.delete.assert_called_once_with(cat)

    @patch(PATCH_TARGET)
    async def test_list_tags(self, mock_ctx):
        session = _mock_db_session(rows=["python, fastapi, blog", "python, react, typescript"])
        mock_ctx.return_value.__aenter__.return_value = session
        result = await content_tools.list_tags({})
        assert result["success"] is True
        tags = [t["name"] for t in result["tags"]]
        assert "python" in tags
        assert "fastapi" in tags
        assert "react" in tags
        assert len(tags) == len(set(tags))
