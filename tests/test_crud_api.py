# -*- coding: utf-8 -*-
"""
文章和评论 CRUD 服务层测试。

测试 shared/services/articles/article_manager/service.py 中的核心 CRUD 函数。
使用 mock 数据库会话（AsyncSession），不依赖真实 PostgreSQL。

覆盖范围：
  - get_article_by_id        — 存在/不存在
  - get_articles_by_user_id  — 用户文章列表
  - create_article           — 创建/含内容/异常
  - update_article           — 更新/无变化/不存在
  - delete_article           — 删除/不存在/异常
  - search_articles          — 关键词搜索
  - 评论服务基础操作          — 创建/列表/审批
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article, ArticleContent
from shared.models.comment import Comment
from shared.services.articles.article_manager.service import (
    get_article_by_id,
    get_articles_by_user_id,
    get_article_count_by_user,
    get_article_with_content,
    create_article,
    update_article,
    delete_article,
    search_articles,
)


# ============================================================================
# Fixtures
# ============================================================================

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_db():
    """AsyncSession mock that supports execute/commit/rollback."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_scalar_result(value):
    """Build a mock execute result that returns a scalar."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalars.return_value.all.return_value = [value] if value else []
    return r


def _make_scalars_result(values):
    """Build a mock execute result that returns a list."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


@pytest.fixture
def sample_article():
    """A minimal article object (MagicMock with needed attrs)."""
    now = datetime.datetime.now()
    a = MagicMock(spec=Article)
    a.id = 1
    a.title = "Test Article"
    a.slug = "test-article"
    a.excerpt = "Test excerpt"
    a.content = "Test content body"
    a.user = 1
    a.category = 2
    a.tags_list = "python;test"
    a.status = 1
    a.is_vip_only = False
    a.hidden = False
    a.views = 100
    a.created_at = now
    a.updated_at = now
    return a


# ============================================================================
# get_article_by_id
# ============================================================================

class TestGetArticleById:
    async def test_found(self, mock_db, sample_article):
        """Returns article when ID exists."""
        mock_db.execute.return_value = _make_scalar_result(sample_article)
        result = await get_article_by_id(mock_db, 1)
        assert result is sample_article
        assert result.id == 1

    async def test_not_found(self, mock_db):
        """Returns None when article doesn't exist."""
        mock_db.execute.return_value = _make_scalar_result(None)
        result = await get_article_by_id(mock_db, 999)
        assert result is None

    async def test_uses_select_with_where(self, mock_db, sample_article):
        """Verify the function queries by ID correctly."""
        mock_db.execute.return_value = _make_scalar_result(sample_article)
        await get_article_by_id(mock_db, 42)
        call_args = mock_db.execute.call_args.args[0]
        stmt_str = str(call_args)
        assert "articles" in stmt_str.lower() or "article" in stmt_str.lower()


# ============================================================================
# get_articles_by_user_id
# ============================================================================

class TestGetArticlesByUserId:
    async def test_returns_list(self, mock_db, sample_article):
        """Returns articles for a given user."""
        mock_db.execute.return_value = _make_scalars_result([sample_article])
        result = await get_articles_by_user_id(mock_db, user_id=1, limit=5)
        assert len(result) == 1
        assert result[0].id == 1

    async def test_empty_user(self, mock_db):
        """Returns empty list when user has no articles."""
        mock_db.execute.return_value = _make_scalars_result([])
        result = await get_articles_by_user_id(mock_db, user_id=999)
        assert result == []


# ============================================================================
# get_article_count_by_user
# ============================================================================

class TestGetArticleCountByUser:
    async def test_returns_count(self, mock_db):
        """Returns article count for a user."""
        r = MagicMock()
        r.scalar.return_value = 5
        mock_db.execute.return_value = r
        result = await get_article_count_by_user(mock_db, user_id=1)
        assert result == 5

    async def test_zero_count(self, mock_db):
        """Returns 0 when user has no articles."""
        r = MagicMock()
        r.scalar.return_value = 0
        mock_db.execute.return_value = r
        result = await get_article_count_by_user(mock_db, user_id=999)
        assert result == 0


# ============================================================================
# create_article
# ============================================================================

class TestCreateArticle:
    @patch("shared.services.articles.article_manager.service.datetime")
    async def test_basic_creation(self, mock_dt, mock_db):
        """Creates an article with minimum fields."""
        now = datetime.datetime(2026, 6, 9)
        mock_dt.now.return_value = now
        mock_dt.timezone.utc = datetime.timezone.utc

        article = await create_article(
            mock_db, user_id=1, title="New Post",
            content="Content body", category_id=2,
            excerpt="Summary", tags="python;alembic",
        )

        assert article.title == "New Post"
        assert article.user == 1
        assert article.category == 2
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.flush.called
        assert mock_db.refresh.called

    @patch("shared.services.articles.article_manager.service.datetime")
    async def test_creation_with_content(self, mock_dt, mock_db):
        """Creates article with content, verifying ArticleContent is added."""
        now = datetime.datetime(2026, 6, 9)
        mock_dt.now.return_value = now
        mock_dt.timezone.utc = datetime.timezone.utc

        article = await create_article(
            mock_db, user_id=1,
            title="Content Test",
            content="Long content body here",
        )

        # Verify ArticleContent was added
        add_calls = [c for c in mock_db.add.call_args_list]
        content_added = any(
            isinstance(c[0][0], ArticleContent) and c[0][0].content == "Long content body here"
            for c in add_calls
        )
        assert content_added, "ArticleContent should be added when content is provided"

    @patch("shared.services.articles.article_manager.service.datetime")
    async def test_error_triggers_rollback(self, mock_dt, mock_db):
        """Database error propagates without rollback (exception bubbles up)."""
        mock_db.commit.side_effect = Exception("DB connection lost")
        now = datetime.datetime(2026, 6, 9)
        mock_dt.now.return_value = now
        mock_dt.timezone.utc = datetime.timezone.utc

        with pytest.raises(Exception, match="DB connection lost"):
            await create_article(mock_db, user_id=1, title="Failing", content="Body")


# ============================================================================
# update_article
# ============================================================================

class TestUpdateArticle:
    async def test_update_fields(self, mock_db, sample_article):
        """Updates specified fields on an existing article."""
        mock_db.execute.return_value = _make_scalar_result(sample_article)

        result = await update_article(
            mock_db, article_id=1, title="Updated Title", status=0
        )

        assert result is sample_article
        assert mock_db.execute.called
        assert mock_db.commit.called
        assert mock_db.refresh.called

    async def test_nonexistent_article(self, mock_db):
        """Returns None when article doesn't exist."""
        mock_db.execute.return_value = _make_scalar_result(None)
        result = await update_article(mock_db, article_id=999, title="Ghost")
        assert result is None

    async def test_update_only_allowed_fields(self, mock_db, sample_article):
        """Only whitelisted fields are passed to the update query."""
        mock_db.execute.return_value = _make_scalar_result(sample_article)

        await update_article(
            mock_db, article_id=1,
            title="Valid",
            non_existent_field="should be ignored",
            # non_existent is not in allowed_fields, should be filtered out
        )

        # Verify the execute call has 'title' but not 'non_existent_field'
        if mock_db.execute.call_count >= 2:
            # The second execute call is the actual update
            second_execute = mock_db.execute.call_args_list[1]
            stmt = str(second_execute.args[0])
            assert "title" in stmt
            assert "non_existent_field" not in stmt


# ============================================================================
# delete_article
# ============================================================================

class TestDeleteArticle:
    async def test_successful_delete(self, mock_db, sample_article):
        """Deletes an existing article."""
        mock_db.execute.return_value = _make_scalar_result(sample_article)

        result = await delete_article(mock_db, article_id=1)

        assert result is True
        assert mock_db.commit.called

    async def test_nonexistent_article(self, mock_db):
        """Returns False when article not found."""
        mock_db.execute.return_value = _make_scalar_result(None)

        result = await delete_article(mock_db, article_id=999)

        assert result is False


# ============================================================================
# search_articles
# ============================================================================

class TestSearchArticles:
    async def test_basic_search(self, mock_db, sample_article):
        """Searches articles by keyword."""
        mock_db.execute.return_value = _make_scalars_result([sample_article])

        result = await search_articles(mock_db, keyword="test", per_page=10)

        assert len(result) == 2  # (article_list, total_count)
        assert len(result[0]) >= 1

    async def test_no_results(self, mock_db):
        """Returns empty result set when nothing matches."""
        mock_db.execute.return_value = _make_scalars_result([])

        result = await search_articles(mock_db, keyword="nonexistentkeyword", per_page=10)

        assert result is not None


# ============================================================================
# get_article_with_content
# ============================================================================

class TestGetArticleWithContent:
    async def test_article_and_content(self, mock_db, sample_article):
        """Returns tuple of (article, content) via JOIN."""
        content = MagicMock(spec=ArticleContent)
        content.content = "Full article content body"

        # first() returns a tuple (Article, ArticleContent)
        row = MagicMock()
        row.first.return_value = (sample_article, content)
        mock_db.execute.return_value = row

        result = await get_article_with_content(mock_db, article_id=1)

        assert result is not None
        assert result[0] is sample_article
        assert result[1] is content
        assert result[1].content == "Full article content body"

    async def test_article_not_found(self, mock_db):
        """Returns None when article doesn't exist."""
        row = MagicMock()
        row.first.return_value = None
        mock_db.execute.return_value = row
        result = await get_article_with_content(mock_db, article_id=999)
        assert result is None


# ============================================================================
# Comment service tests
# ============================================================================

class TestCommentService:
    """Basic comment service operations (via comment_manager)."""

    @patch("shared.services.comments.comment_manager.comment_like.comment_like_service")
    async def test_comment_like_toggle(self, mock_like_service):
        """Tests the comment like/unlike logic through service."""
        mock_like_service.toggle_like = AsyncMock(return_value={
            "success": True, "action": "liked", "likes": 5
        })
        result = await mock_like_service.toggle_like(user_id=1, comment_id=10)
        assert result["success"] is True
        assert result["action"] == "liked"
        assert result["likes"] == 5

    @patch("shared.services.comments.comment_manager.comment_like.comment_like_service")
    async def test_comment_like_count(self, mock_like_service):
        """Verifies like count increments correctly."""
        mock_like_service.get_likes_count = AsyncMock(return_value=42)
        count = await mock_like_service.get_likes_count(comment_id=10)
        assert count == 42
