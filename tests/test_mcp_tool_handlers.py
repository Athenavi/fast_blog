# -*- coding: utf-8 -*-
"""
MCP 工具 handler 测试。

测试新增的 12 个 MCP 工具 handler 在 mocked 数据库环境下的行为。
覆盖：
  - 评论: list_comments / approve_comment / reject_comment / delete_comment
  - 分析: get_analytics / get_trending_articles
  - 媒体: list_media / delete_media
  - 标签/分类: update_category / delete_category / list_tags
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp.server import mcp_server

pytestmark = pytest.mark.asyncio


# ============================================================================
# 辅助函数
# ============================================================================

def _mock_db_session(rows=None, scalar=None):
    """创建 mock 数据库会话，支持 execute 返回值配置."""
    session = AsyncMock()
    execute_result = MagicMock()

    if rows is not None:
        execute_result.scalars.return_value.all.return_value = rows
    if scalar is not None:
        execute_result.scalar_one_or_none.return_value = scalar
        execute_result.scalar.return_value = scalar

    session.execute.return_value = execute_result
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


def _mock_article(**kwargs):
    """创建 mock Article 对象."""
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
    """创建 mock Comment 对象."""
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
    """创建 mock Media 对象."""
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
    """list_comments / approve_comment / reject_comment / delete_comment"""

    @patch("src.mcp.server.get_async_session_context")
    async def test_list_comments(self, mock_ctx):
        """list_comments 返回评论列表."""
        comments = [_mock_comment(id=1, content="First"), _mock_comment(id=2, content="Second")]
        session = _mock_db_session(rows=comments)
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._list_comments_tool({"status": "pending", "limit": 20})

        assert result["success"] is True
        assert len(result["comments"]) == 2
        assert result["comments"][0]["content"] == "First"

    @patch("src.mcp.server.get_async_session_context")
    async def test_approve_comment(self, mock_ctx):
        """approve_comment 将 is_approved 设为 True."""
        comment = _mock_comment(id=42, is_approved=False)
        session = _mock_db_session(scalar=comment)
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._approve_comment_tool({"comment_id": 42})

        assert result["success"] is True
        assert comment.is_approved is True
        session.commit.assert_called_once()

    @patch("src.mcp.server.get_async_session_context")
    async def test_reject_comment(self, mock_ctx):
        """reject_comment 将 is_approved 设为 False."""
        comment = _mock_comment(id=7, is_approved=True)
        session = _mock_db_session(scalar=comment)
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._reject_comment_tool({"comment_id": 7})

        assert result["success"] is True
        assert comment.is_approved is False



# ============================================================================
# 分析工具
# ============================================================================

class TestAnalyticsTools:
    """get_analytics / get_trending_articles"""

    @patch("src.mcp.server.get_async_session_context")
    async def test_get_analytics(self, mock_ctx):
        """get_analytics 返回博客统计概况."""
        session = _mock_db_session(scalar=42)
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._get_analytics_tool({})

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["articles"]["published"] == 42
        assert result["data"]["users"] == 42

    @patch("src.mcp.server.get_async_session_context")
    async def test_get_trending_articles(self, mock_ctx):
        """get_trending_articles 返回热门文章."""
        articles = [_mock_article(id=1, title="Top 1", views=500)]
        session = _mock_db_session(rows=articles, scalar=None)
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._get_trending_articles_tool({"limit": 5, "days": 7})

        assert result["success"] is True
        assert len(result["articles"]) == 1
        assert result["articles"][0]["title"] == "Top 1"


# ============================================================================
# 媒体工具
# ============================================================================

class TestMediaTools:
    """list_media / delete_media"""

    @patch("src.mcp.server.get_async_session_context")
    async def test_list_media(self, mock_ctx):
        """list_media 返回媒体列表."""
        media = [_mock_media(id=1, filename="img1.jpg"), _mock_media(id=2, filename="vid.mp4", mime_type="video/mp4")]
        session = _mock_db_session(rows=media)
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._list_media_tool({"limit": 10})

        assert result["success"] is True
        assert len(result["media"]) == 2
        assert result["media"][0]["filename"] == "photo.jpg"

    @patch("src.mcp.server.get_async_session_context")
    async def test_list_media_with_type_filter(self, mock_ctx):
        """list_media 支持 media_type 筛选."""
        session = _mock_db_session(rows=[])
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._list_media_tool({"media_type": "image", "limit": 5})

        assert result["success"] is True
        # Verify the query includes mime_type filter
        call_args = session.execute.call_args[0][0]
        assert "mime_type" in str(call_args)

    @patch("src.mcp.server.get_async_session_context")
    async def test_delete_media(self, mock_ctx):
        """delete_media 删除媒体."""
        media = _mock_media(id=5)
        session = _mock_db_session(scalar=media)
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._delete_media_tool({"media_id": 5})

        assert result["success"] is True
        session.delete.assert_called_once_with(media)


# ============================================================================
# 分类/标签工具
# ============================================================================

class TestCategoryTagTools:
    """update_category / delete_category / list_tags"""

    @patch("src.mcp.server.get_async_session_context")
    async def test_update_category(self, mock_ctx):
        """update_category 更新分类名称."""
        cat = MagicMock()
        cat.id = 3
        cat.name = "Old Name"
        cat.slug = "old-name"
        cat.updated_at = None

        session = _mock_db_session(scalar=cat)
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._update_category_tool({"category_id": 3, "name": "New Name"})

        assert result["success"] is True
        assert cat.name == "New Name"
        session.commit.assert_called_once()

    @patch("src.mcp.server.get_async_session_context")
    async def test_delete_category(self, mock_ctx):
        """delete_category 删除分类."""
        cat = MagicMock()
        cat.id = 7
        session = _mock_db_session(scalar=cat)
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._delete_category_tool({"category_id": 7})

        assert result["success"] is True
        session.delete.assert_called_once_with(cat)

    @patch("src.mcp.server.get_async_session_context")
    async def test_list_tags(self, mock_ctx):
        """list_tags 从文章聚合标签并去重."""
        # Handler selects Article.tags_list column, so mock returns strings
        session = _mock_db_session(rows=["python, fastapi, blog", "python, react, typescript"])
        mock_ctx.return_value.__aenter__.return_value = session

        result = await mcp_server._list_tags_tool({})

        assert result["success"] is True
        tags = [t["name"] for t in result["tags"]]
        assert "python" in tags
        assert "fastapi" in tags
        assert "react" in tags
        # 去重验证
        assert len(tags) == len(set(tags))
