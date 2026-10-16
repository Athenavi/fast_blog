# -*- coding: utf-8 -*-
"""短代码展开回归测试

``shortcodes`` 表此前**只有 CRUD、没有任何展开逻辑**（全仓搜不到
``apply_shortcode`` / ``render_shortcode`` / ``replace_shortcode``），
也就是短代码存进库里对正文毫无影响。这里锁定 ``expand_for_content`` 的四条行为：

1. 启用中的 ``[code]`` 被替换成对应 ``content``；
2. 未登记 / 已停用的 ``code`` **原样保留**（正文里的方括号不能被吃掉）；
3. **不递归展开**（互相引用的短代码不会无限展开）；
4. **多租户**：站点专属优先于全局（``site_id IS NULL``）回落。

另外锁一条性能约束：正文里没有短代码时**不查库**。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.v3.modules.content.shortcode.service import (
    ShortcodeService,
    _SHORTCODE_PATTERN,
)


def _row(code: str, content: str, site_id=None) -> MagicMock:
    row = MagicMock()
    row.code = code
    row.content = content
    row.site_id = site_id
    return row


def _db_returning(rows: list) -> AsyncMock:
    """构造 db，使其 ``execute(...).scalars().all()`` 返回给定行"""
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    db.execute = AsyncMock(return_value=result)
    return db


_svc = ShortcodeService()


@pytest.mark.unit
class TestExpandShortcodes:
    @pytest.mark.asyncio
    async def test_expands_registered_code(self):
        db = _db_returning([_row("ad-banner", "<div class='ad'>买它</div>")])
        out = await _svc.expand_for_content(db, "前言\n\n[ad-banner]\n\n后记")
        assert "<div class='ad'>买它</div>" in out
        assert "[ad-banner]" not in out
        assert "前言" in out and "后记" in out

    @pytest.mark.asyncio
    async def test_unknown_code_is_kept_verbatim(self):
        """查不到的 code 原样保留 —— 正文里的方括号是常事"""
        db = _db_returning([])
        out = await _svc.expand_for_content(db, "见 [nope] 与 [ref-1]")
        assert out == "见 [nope] 与 [ref-1]"

    @pytest.mark.asyncio
    async def test_inactive_code_is_kept(self):
        """已停用的短代码不会被替换（查询已过滤 is_active，这里模拟查不到）"""
        db = _db_returning([])
        out = await _svc.expand_for_content(db, "[disabled-one]")
        assert out == "[disabled-one]"

    @pytest.mark.asyncio
    async def test_does_not_recurse(self):
        """替换内容里再出现 [code] 不再展开（否则互相引用会无限展开）"""
        db = _db_returning([_row("a", "[b]"), _row("b", "[a]")])
        out = await _svc.expand_for_content(db, "[a]")
        assert out == "[b]", "不应递归展开，[b] 必须原样保留"

    @pytest.mark.asyncio
    async def test_site_specific_wins_over_global(self):
        """站点专属条目优先于全局（site_id IS NULL）回落"""
        rows = [
            _row("promo", "<p>全局</p>", site_id=None),
            _row("promo", "<p>本站</p>", site_id=7),
        ]
        db = _db_returning(rows)
        out = await _svc.expand_for_content(db, "[promo]", site_id=7)
        assert out == "<p>本站</p>"

    @pytest.mark.asyncio
    async def test_global_used_when_no_site_specific(self):
        rows = [_row("promo", "<p>全局</p>", site_id=None)]
        db = _db_returning(rows)
        out = await _svc.expand_for_content(db, "[promo]", site_id=7)
        assert out == "<p>全局</p>"

    @pytest.mark.asyncio
    async def test_multiple_codes_single_query(self):
        """一次查询解决多个 code（正文里可能有几十个短代码）"""
        rows = [_row("a", "A"), _row("b", "B")]
        db = _db_returning(rows)
        out = await _svc.expand_for_content(db, "[a]-[b]")
        assert out == "A-B"
        assert db.execute.await_count == 1, "应按 IN 一次查询，而不是逐个查"

    @pytest.mark.asyncio
    async def test_no_shortcode_skips_query(self):
        """正文里没有短代码时不该查库"""
        db = _db_returning([])
        out = await _svc.expand_for_content(db, "纯正文，没有短代码")
        assert out == "纯正文，没有短代码"
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_content_passthrough(self):
        db = _db_returning([])
        assert await _svc.expand_for_content(db, None) is None
        assert await _svc.expand_for_content(db, "") == ""
        db.execute.assert_not_awaited()

    def test_pattern_matches_schema_charset(self):
        """正则字符集必须与 ShortcodeCreate.code 的 pattern 一致"""
        assert _SHORTCODE_PATTERN.findall("[ad-banner]") == ["ad-banner"]
        assert _SHORTCODE_PATTERN.findall("[promo_2]") == ["promo_2"]
        # 大写与空格不在 schema 允许的字符集内，不应被当作短代码
        assert _SHORTCODE_PATTERN.findall("[AD Banner]") == []


@pytest.mark.unit
class TestRenderPipelineOrder:
    """短代码必须先于 Markdown/净化展开（否则替换内容绕过 XSS 防线）"""

    @pytest.mark.asyncio
    async def test_shortcode_expansion_precedes_sanitize(self):
        from src.api.v3.modules.content.article.service import ArticleService

        svc = ArticleService()
        # 替换内容里带 <script>：必须被净化掉，证明它走了 sanitize 管线
        db = _db_returning([_row("evil", "<script>alert(1)</script><p>ok</p>")])
        data = {"content": "[evil]"}

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "src.api.v3.modules.content.article.service.shortcode_service.expand_for_content",
                AsyncMock(return_value="<script>alert(1)</script><p>ok</p>"),
            )
            out = await svc._render_content_for_display(db, data)

        assert "<script>" not in out["content"], "短代码注入的脚本必须被净化"
        assert "ok" in out["content"]
