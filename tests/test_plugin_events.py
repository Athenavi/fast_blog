# -*- coding: utf-8 -*-
"""插件事件链路回归测试

覆盖两个**叠加**导致扩展点完全失效的缺陷：

1. **事件名不一致**：核心发下划线名（``article_published``），而订阅方
   （``plugins/seo``、``plugins/newsletter``、``audit_subscriber``）用点号名
   （``article.published``）—— 两边对不上，订阅从未被触发。
2. **v3 文章 CRUD 不发事件**：``src/api/v3/modules/content/article/service.py``
   才是 v3 实际使用的写入路径，而它的 create/update/delete 里没有任何 emit。

这里断言的是**契约**（事件名）与**链路**（写入是否真的发出事件），
而不是某个插件的行为 —— 后者会随插件实现变化而失效。
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.services.plugins.event_bus import event_bus

#: 仓库根（tests/ 的上一级）
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _clean_bus():
    """每个用例前后清空订阅

    ``EventBus.clear`` 的 docstring 就写着"主要用于测试"，这里遵循该约定，
    避免本文件的订阅泄漏到其它用例。
    """
    event_bus.clear()
    yield
    event_bus.clear()


@pytest.mark.unit
class TestEventNameContract:
    """核心发出的事件名必须与订阅方一致 —— 否则订阅是静默失效的"""

    def test_article_manager_uses_dotted_names(self):
        """``article_manager`` 触发的事件名必须是点号

        用源码断言而非运行时调用：``_trigger_article_event`` 内部走
        ``asyncio.create_task`` 且需要 DB 会话，源码级断言足以锁定契约
        （一旦有人改回下划线名，这里立刻变红）。
        """
        src = (
            ROOT / "shared" / "services" / "articles" / "article_manager" / "service.py"
        ).read_text(encoding="utf-8")

        for name in ("article.published", "article.updated", "article.deleted"):
            assert f"_trigger_article_event('{name}'" in src, f"缺少点号事件名 {name}"

        # 历史遗留的下划线名必须已清零
        for legacy in ("article_published", "article_updated", "article_deleted"):
            assert f"_trigger_article_event('{legacy}'" not in src, (
                f"仍在使用下划线事件名 {legacy}（订阅方用点号，收不到）"
            )

    def test_subscribers_use_dotted_names(self):
        """订阅方的订阅名必须是点号（与核心发出的名字对齐）

        直接检查真实的插件源码与审计订阅表，而不是复制一份"期望值"——
        这样核心改了名字、插件没跟上的情况也能被发现。
        """
        sources = [
            ROOT / "plugins" / "seo" / "plugin.py",
            ROOT / "plugins" / "newsletter" / "plugin.py",
            ROOT / "shared" / "services" / "security" / "audit_subscriber.py",
        ]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            assert '"article.published"' in text or "'article.published'" in text, (
                f"{path.name} 未订阅 article.published"
            )


@pytest.mark.unit
class TestV3ArticleEvents:
    """v3 的文章 CRUD 必须真的发出事件，否则订阅方永远收不到"""

    def _fake_article(self) -> MagicMock:
        article = MagicMock()
        article.id = 42
        article.slug = "hello"
        article.title = "Hello"
        article.user = 7
        article.excerpt = "ex"
        article.tags_list = "a;b"
        article.category = 3
        return article

    @pytest.mark.asyncio
    async def test_create_article_emits_published(self):
        """``create_article`` → 订阅 ``article.published`` 的处理器被调用"""
        from src.api.v3.modules.content.article.crud import article_crud
        from src.api.v3.modules.content.article.schema import ArticleCreate
        from src.api.v3.modules.content.article.service import ArticleService

        received: list = []

        async def on_published(payload):
            received.append(payload)

        event_bus.listen("article.published", on_published)

        svc = ArticleService()
        with patch.object(article_crud, "create", AsyncMock(return_value=self._fake_article())), \
            patch.object(svc, "_invalidate", AsyncMock()), \
            patch.object(svc, "get_article", AsyncMock(return_value={"id": 42})):
            await svc.create_article(
                AsyncMock(), ArticleCreate(title="Hello"), user_id=7
            )

        assert len(received) == 1, "create_article 必须发出 article.published"
        payload = received[0]
        assert payload.article_id == 42
        assert payload.title == "Hello"
        assert payload.author_id == 7
        assert payload.tags == ["a", "b"]

    @pytest.mark.asyncio
    async def test_update_article_emits_updated(self):
        """``update_article`` → 订阅 ``article.updated`` 的处理器被调用"""
        from src.api.v3.modules.content.article.crud import article_crud
        from src.api.v3.modules.content.article.schema import ArticleUpdate
        from src.api.v3.modules.content.article.service import ArticleService

        received: list = []

        async def on_updated(payload):
            received.append(payload)

        event_bus.listen("article.updated", on_updated)

        existing = self._fake_article()
        existing.status = 0
        svc = ArticleService()
        with patch.object(article_crud, "get", AsyncMock(return_value=existing)), \
            patch.object(article_crud, "update", AsyncMock(return_value=existing)), \
            patch.object(svc, "_invalidate", AsyncMock()), \
            patch.object(svc, "get_article", AsyncMock(return_value={"id": 42})):
            await svc.update_article(AsyncMock(), 42, ArticleUpdate(title="New"))

        assert len(received) == 1, "update_article 必须发出 article.updated"
        assert received[0].article_id == 42

    @pytest.mark.asyncio
    async def test_delete_article_emits_deleted(self):
        """``delete_article`` → 订阅 ``article.deleted`` 的处理器被调用"""
        from src.api.v3.modules.content.article.crud import article_crud
        from src.api.v3.modules.content.article.service import ArticleService

        received: list = []

        async def on_deleted(payload):
            received.append(payload)

        event_bus.listen("article.deleted", on_deleted)

        svc = ArticleService()
        with patch.object(article_crud, "get", AsyncMock(return_value=self._fake_article())), \
            patch.object(article_crud, "update", AsyncMock(return_value=self._fake_article())), \
            patch.object(svc, "_invalidate", AsyncMock()):
            await svc.delete_article(AsyncMock(), 42)

        assert len(received) == 1, "delete_article 必须发出 article.deleted"
        assert received[0].article_id == 42


@pytest.mark.unit
class TestEventBusResilience:
    """订阅方抛异常不能影响文章写入主流程（插件是可选组件）"""

    @pytest.mark.asyncio
    async def test_subscriber_exception_does_not_break_write(self):
        from src.api.v3.modules.content.article.crud import article_crud
        from src.api.v3.modules.content.article.schema import ArticleCreate
        from src.api.v3.modules.content.article.service import ArticleService

        async def boom(payload):
            raise RuntimeError("插件炸了")

        event_bus.listen("article.published", boom)

        svc = ArticleService()
        article = MagicMock()
        article.id = 42
        article.slug = "hello"
        article.title = "Hello"
        article.user = 7
        article.excerpt = ""
        article.tags_list = ""
        article.category = None

        with patch.object(article_crud, "create", AsyncMock(return_value=article)), \
            patch.object(svc, "_invalidate", AsyncMock()), \
            patch.object(svc, "get_article", AsyncMock(return_value={"id": 42})):
            # 不应抛出
            result = await svc.create_article(
                AsyncMock(), ArticleCreate(title="Hello"), user_id=7
            )

        assert result == {"id": 42}
