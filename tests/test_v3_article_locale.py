# -*- coding: utf-8 -*-
"""P1-4 多语言：locale 解析与正文回退链（纯函数 + 轻量假 DB，不连数据库）。

事实前提：``article_content`` 本来就是"一行一语言"，所以多语言缺的不是存储，
而是**回退链**与 **locale 归一**。本文件钉住这两点：

  1. ``zh-cn``/``en_US``/``zh-hans`` 等写法能归一到统一形态；
  2. 请求语言缺失时按 ``zh-CN`` → ``zh`` → 默认语言 回退，并且**如实回传实际语言**；
  3. ``Accept-Language`` 解析支持 q 值排序、跳过 ``*`` 与 ``q=0``；
  4. 链完全不命中时退到该文章已有语言（不是返回空）。
"""

from typing import List, Optional

import pytest

from src.api.v3.modules.content.article.locale import (
    DEFAULT_LOCALE,
    fallback_chain,
    normalize_locale,
    parse_accept_language,
    pick_locale,
    resolve_requested_locale,
)
from src.api.v3.modules.content.article.service import article_service


# ---------------------------------------------------------------- 归一与回退链

class TestNormalize:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("zh-cn", "zh-CN"),
            ("ZH-CN", "zh-CN"),
            ("en_US", "en-US"),
            ("en-us", "en-US"),
            ("zh-hans", "zh-CN"),  # 常见中文别名
            ("zh-hant", "zh-TW"),
            ("ja", "ja"),
        ],
    )
    def test_normalize(self, raw, expected):
        assert normalize_locale(raw) == expected

    def test_empty_uses_default(self):
        assert normalize_locale(None, default=DEFAULT_LOCALE) == DEFAULT_LOCALE
        assert normalize_locale("  ") == ""


class TestFallbackChain:
    def test_regional_locale_falls_back_to_primary(self):
        # 默认语言与请求相同，因此链尾的 default 被去重
        assert fallback_chain("zh-CN") == ["zh-CN", "zh"]

    def test_primary_only(self):
        assert fallback_chain("ja") == ["ja", DEFAULT_LOCALE]

    def test_empty_gives_default_only(self):
        assert fallback_chain(None) == [DEFAULT_LOCALE]

    def test_chain_is_deduplicated(self):
        chain = fallback_chain(DEFAULT_LOCALE)
        assert chain[0] == DEFAULT_LOCALE
        assert chain.count(DEFAULT_LOCALE) == 1, "默认语言不应在链里重复出现"

    def test_custom_default(self):
        assert fallback_chain("fr", default="en") == ["fr", "en"]


class TestAcceptLanguage:
    def test_sorted_by_quality(self):
        header = "en-US;q=0.6, zh-CN;q=0.9, ja;q=0.3"
        assert parse_accept_language(header) == ["zh-CN", "en-US", "ja"]

    def test_default_quality_and_order_preserved(self):
        assert parse_accept_language("zh-CN,en") == ["zh-CN", "en"]

    def test_wildcard_and_zero_quality_skipped(self):
        assert parse_accept_language("*;q=1, en;q=0, ja;q=0.5") == ["ja"]

    def test_empty_header(self):
        assert parse_accept_language("") == []
        assert parse_accept_language(None) == []

    def test_limit(self):
        header = ",".join(f"l{i}" for i in range(10))
        assert len(parse_accept_language(header, limit=3)) == 3


class TestResolveRequestedLocale:
    def test_explicit_locale_wins(self):
        chain = resolve_requested_locale("ja", "zh-CN,en")
        assert chain[:2] == ["ja", DEFAULT_LOCALE]

    def test_accept_language_used_when_no_explicit(self):
        chain = resolve_requested_locale(None, "ja,zh-CN")
        assert chain[0] == "ja", "无显式 locale 时链首必须是 Accept-Language 的首选，而非默认语言"
        assert DEFAULT_LOCALE in chain

    def test_no_hints_gives_default(self):
        assert resolve_requested_locale(None, None) == [DEFAULT_LOCALE]


class TestPickLocale:
    def test_case_insensitive_hit(self):
        assert pick_locale(["zh-cn", "en"], ["zh-CN", "zh"]) == "zh-cn"

    def test_falls_through_chain(self):
        assert pick_locale(["zh", "en"], ["zh-CN", "zh", "en"]) == "zh"

    def test_no_hit_returns_none(self):
        assert pick_locale(["de"], ["zh-CN", "zh"]) is None


# ---------------------------------------------------------------- service 回退

class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, stmt):  # noqa: ARG002
        return _Scalars(self._rows)


class _FakeContent:
    def __init__(self, language_code: Optional[str], content: str = "") -> None:
        self.language_code = language_code
        self.content = content


@pytest.mark.asyncio
class TestContentFallback:
    async def test_exact_match(self):
        rows = [_FakeContent("en", "hello"), _FakeContent("zh-CN", "你好")]
        row, resolved = await article_service._content_row_by_chain(
            _FakeDB(rows), 1, locale="en"
        )
        assert row.content == "hello" and resolved == "en"

    async def test_regional_request_falls_back_to_primary(self):
        rows = [_FakeContent("zh", "你好")]
        row, resolved = await article_service._content_row_by_chain(
            _FakeDB(rows), 1, locale="zh-CN"
        )
        assert row.content == "你好"
        assert resolved == "zh", "应如实回传实际命中的语言（前端据此提示回退）"

    async def test_falls_back_to_default_locale(self):
        rows = [_FakeContent("zh-CN", "默认")]
        row, resolved = await article_service._content_row_by_chain(
            _FakeDB(rows), 1, locale="ja"
        )
        assert resolved == "zh-CN" and row.content == "默认"

    async def test_chain_miss_falls_back_to_any_available(self):
        rows = [_FakeContent("de", "hallo")]
        row, resolved = await article_service._content_row_by_chain(
            _FakeDB(rows), 1, locale="ja"
        )
        assert resolved == "de", "链都不命中时退到已有语言，而不是返回空"

    async def test_no_content_rows(self):
        row, resolved = await article_service._content_row_by_chain(_FakeDB([]), 1, locale="en")
        assert row is None and resolved is None

    async def test_accept_language_used_when_locale_absent(self):
        rows = [_FakeContent("ja", "こんにちは"), _FakeContent("zh-CN", "你好")]
        row, resolved = await article_service._content_row_by_chain(
            _FakeDB(rows), 1, accept_language="ja;q=0.9, zh-CN;q=0.2"
        )
        assert resolved == "ja" and row.content == "こんにちは"

    async def test_available_locales_dedupes_in_order(self):
        rows: List[Optional[str]] = ["zh-CN", "en", "zh-CN", None]
        locales = await article_service.available_locales(_FakeDB(rows), 1)
        assert locales == ["zh-CN", "en"]
