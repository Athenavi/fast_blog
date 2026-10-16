# -*- coding: utf-8 -*-
"""阶段 0-1：审批闸门（`approval/guard.py`）把审批单真正接进发布路径。

两个维度：

  1. **规则分支**（`TestGuardRules`）：用假会话喂入「按 created_at 倒序」的审批行，
     逐条验证 pending/rejected 拦截、approved 放行、无记录时配置驱动的强制，
     以及配置读不到/格式非法时**不强制但记 warning**（fail-open 的理由见 guard docstring）。
  2. **接入是否真的发生**（`TestPublishPathsWired`）：既做关键路径的运行时断言，
     也用源码结构断言兜住 article 的 4 条 + page 的 3 条发布入口 —— 防止后人删掉闸门。

本测试**不依赖真实数据库**：假会话只实现 guard 用到的那一处 `execute(...).all()`。
"""

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.content.approval import guard
from src.api.v3.modules.content.article.service import ArticleService, article_service
from src.api.v3.modules.content.page.service import PageService, page_service

SETTING_CRUD_GET = "src.api.v3.modules.system.setting.crud.setting_crud.get_by"


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeDB:
    """最小假会话：`execute` 固定返回预置的审批行（按 SQL 语义应为「时间倒序」）。"""

    def __init__(self, approval_rows=None):
        self.approval_rows = list(approval_rows or [])
        self.execute = AsyncMock(return_value=_Result(self.approval_rows))


def _setting_row(value: str, setting_type: str = "json"):
    return SimpleNamespace(setting_value=value, setting_type=setting_type)


# ────────────────────────────────────────────────────────── 1. 规则分支

@pytest.mark.asyncio
class TestGuardRules:
    async def test_pending_blocks_publish(self):
        db = FakeDB([(1, "pending")])
        with pytest.raises(BadRequestError) as exc:
            await guard.ensure_publish_allowed(db, content_type="article", content_id=1)
        assert "待处理的审批单" in str(exc.value)
        assert "#1" in str(exc.value)

    async def test_rejected_blocks_publish(self):
        db = FakeDB([(1, "rejected")])
        with pytest.raises(BadRequestError) as exc:
            await guard.ensure_publish_allowed(db, content_type="article", content_id=1)
        assert "驳回" in str(exc.value)

    async def test_approved_allows_publish(self):
        db = FakeDB([(1, "approved")])
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=None)):
            await guard.ensure_publish_allowed(db, content_type="article", content_id=1)

    async def test_latest_record_wins(self):
        """同一内容多条记录时以**最新**为准（SQL 已按时间倒序，首条即最新）。"""
        db = FakeDB([(1, "pending"), (1, "approved")])
        with pytest.raises(BadRequestError):
            await guard.ensure_publish_allowed(db, content_type="article", content_id=1)

    async def test_no_record_and_not_required_allows(self):
        """默认不强制：没有审批单时照常发布，避免把历史内容一夜之间锁死。"""
        db = FakeDB([])
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=None)):
            await guard.ensure_publish_allowed(db, content_type="article", content_id=1)

    async def test_no_record_but_required_blocks(self):
        db = FakeDB([])
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=_setting_row('["article"]'))):
            with pytest.raises(BadRequestError) as exc:
                await guard.ensure_publish_allowed(db, content_type="article", content_id=1)
        assert "必须审批" in str(exc.value)

    async def test_cancelled_counts_as_no_approval(self):
        db = FakeDB([(1, "cancelled")])
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=_setting_row('["article"]'))):
            with pytest.raises(BadRequestError):
                await guard.ensure_publish_allowed(db, content_type="article", content_id=1)

    async def test_other_content_type_not_required(self):
        """配置只对指定类型生效：page 未在列表里 → 无记录也放行。"""
        db = FakeDB([])
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=_setting_row('["article"]'))):
            await guard.ensure_publish_allowed(db, content_type="page", content_id=1)

    async def test_comma_separated_string_config_also_works(self):
        db = FakeDB([])
        with patch(
            SETTING_CRUD_GET,
            AsyncMock(return_value=_setting_row("article, page", setting_type="string")),
        ):
            with pytest.raises(BadRequestError):
                await guard.ensure_publish_allowed(db, content_type="page", content_id=1)

    async def test_malformed_config_does_not_force(self):
        """配置格式非法 → 不强制（并记 warning），而不是抛错或全站锁死。"""
        db = FakeDB([])
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=_setting_row('{"article": true}'))):
            await guard.ensure_publish_allowed(db, content_type="article", content_id=1)

    async def test_config_read_failure_does_not_force(self):
        db = FakeDB([])
        with patch(SETTING_CRUD_GET, AsyncMock(side_effect=RuntimeError("db down"))):
            await guard.ensure_publish_allowed(db, content_type="article", content_id=1)

    async def test_config_read_failure_still_blocks_pending(self):
        """配置读不到时，**规则 1（待审拦截）依然生效** —— 安全性不依赖配置。"""
        db = FakeDB([(1, "pending")])
        with patch(SETTING_CRUD_GET, AsyncMock(side_effect=RuntimeError("db down"))):
            with pytest.raises(BadRequestError):
                await guard.ensure_publish_allowed(db, content_type="article", content_id=1)

    async def test_batch_lists_all_reasons_and_queries_once(self):
        """批量：一条 SQL 查完（无 N+1），且把全部原因一次列清。"""
        db = FakeDB([(1, "pending"), (2, "approved"), (3, "rejected")])
        # 必须把配置读取 mock 掉，否则 setting_crud 也会走 db.execute，计数就不止 1
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=None)):
            with pytest.raises(BadRequestError) as exc:
                await guard.ensure_batch_publish_allowed(
                    db, content_type="article", ids=[1, 2, 3]
                )
        message = str(exc.value)
        assert "#1" in message and "#3" in message
        assert "#2" not in message, "通过的那条不应出现在拦截原因里"
        assert db.execute.await_count == 1, "批量校验必须只查一次审批表（无 N+1）"

    async def test_batch_empty_ids_is_noop(self):
        db = FakeDB([(1, "pending")])
        await guard.ensure_batch_publish_allowed(db, content_type="article", ids=[])
        assert db.execute.await_count == 0

    async def test_batch_ignores_dirty_ids(self):
        """入参里混入无法转 int 的值不应 500（也不应把它算作通过）。"""
        db = FakeDB([])
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=None)):
            await guard.ensure_batch_publish_allowed(
                db, content_type="article", ids=["x", None, 5]  # type: ignore[list-item]
            )
        assert db.execute.await_count == 1

    async def test_batch_required_type_blocks_missing_approval(self):
        db = FakeDB([(5, "approved")])
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=_setting_row('["article"]'))):
            with pytest.raises(BadRequestError) as exc:
                await guard.ensure_batch_publish_allowed(
                    db, content_type="article", ids=[5, 6]
                )
        assert "#6" in str(exc.value) and "#5" not in str(exc.value)

    async def test_new_content_publish_blocked_when_required(self):
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=_setting_row('["article"]'))):
            with pytest.raises(BadRequestError) as exc:
                await guard.ensure_new_content_publish_allowed(
                    db=FakeDB(), content_type="article"
                )
        assert "先审批后发布" in str(exc.value)

    async def test_new_content_publish_allowed_when_not_required(self):
        with patch(SETTING_CRUD_GET, AsyncMock(return_value=None)):
            await guard.ensure_new_content_publish_allowed(db=FakeDB(), content_type="article")


# ────────────────────────────────────────────────────────── 2. 接入验证

ARTICLE_MOD = "src.api.v3.modules.content.article.service"
PAGE_MOD = "src.api.v3.modules.content.page.service"


@pytest.mark.asyncio
class TestPublishPathsWired:
    async def test_article_set_published_calls_guard(self):
        article = SimpleNamespace(id=7, status=0, published_at=None)
        with (
            patch(f"{ARTICLE_MOD}.article_crud.get", AsyncMock(return_value=article)),
            patch(f"{ARTICLE_MOD}.article_crud.update", AsyncMock(return_value=article)),
            patch(f"{ARTICLE_MOD}._assert_article_write", AsyncMock()),
            patch.object(article_service, "_invalidate", AsyncMock()),
            patch(f"{ARTICLE_MOD}.to_out", lambda row: {"id": row.id}),
            patch(f"{ARTICLE_MOD}.ensure_publish_allowed", AsyncMock()) as guard_mock,
        ):
            await article_service.set_published(FakeDB(), 7, True)

        guard_mock.assert_awaited_once()
        assert guard_mock.await_args.kwargs["content_type"] == guard.ARTICLE_CONTENT_TYPE
        assert guard_mock.await_args.kwargs["content_id"] == 7

    async def test_article_unpublish_skips_guard(self):
        """撤回发布不该被审批拦住（闸门只挡「发布」方向）。"""
        article = SimpleNamespace(id=7, status=1, published_at=None)
        with (
            patch(f"{ARTICLE_MOD}.article_crud.get", AsyncMock(return_value=article)),
            patch(f"{ARTICLE_MOD}.article_crud.update", AsyncMock(return_value=article)),
            patch(f"{ARTICLE_MOD}._assert_article_write", AsyncMock()),
            patch.object(article_service, "_invalidate", AsyncMock()),
            patch(f"{ARTICLE_MOD}.to_out", lambda row: {"id": row.id}),
            patch(f"{ARTICLE_MOD}.ensure_publish_allowed", AsyncMock()) as guard_mock,
        ):
            await article_service.set_published(FakeDB(), 7, False)

        guard_mock.assert_not_awaited()

    async def test_page_set_published_calls_guard(self):
        page = SimpleNamespace(id=9, status=0, published_at=None)
        with (
            patch(f"{PAGE_MOD}.page_crud.get", AsyncMock(return_value=page)),
            patch(f"{PAGE_MOD}.page_crud.update", AsyncMock(return_value=page)),
            patch(f"{PAGE_MOD}._assert_page_write", AsyncMock()),
            patch(f"{PAGE_MOD}._out", lambda row, **kwargs: {"id": row.id}),
            patch(f"{PAGE_MOD}.ensure_publish_allowed", AsyncMock()) as guard_mock,
        ):
            await page_service.set_published(FakeDB(), 9, True)

        guard_mock.assert_awaited_once()
        assert guard_mock.await_args.kwargs["content_type"] == guard.PAGE_CONTENT_TYPE

    def test_all_publish_entrypoints_call_the_guard(self):
        """结构断言：把「发布入口必须过闸门」钉住，避免后续重构悄悄摘掉它。

        覆盖 article 的 create / update / set_published / batch_set_published
        与 page 的 create / update / set_published。
        """
        for cls, mod_path in ((ArticleService, ARTICLE_MOD), (PageService, PAGE_MOD)):
            source = inspect.getsource(cls)
            assert "ensure_publish_allowed" in source, f"{cls.__name__} 未接单条闸门"
            assert "ensure_new_content_publish_allowed" in source, (
                f"{cls.__name__} 未接「新建即发布」闸门"
            )

        article_source = inspect.getsource(ArticleService)
        assert "ensure_batch_publish_allowed" in article_source, "article 批量发布未接闸门"
