"""_pending_test_translation.py —— 待迁入 ``tests/`` 的**纯函数**单测

本任务的环境**禁止写 ``tests/`` 目录、禁止执行 shell**，因此把翻译模块的纯函数单测
临时放在模块目录内（文件名以 ``_pending_`` 开头，不会被当作业务模块导入）。
恢复后应移动到 ``tests/api/v3/system/test_translation.py``。

只覆盖**不依赖 DB / 网络 / FastAPI** 的纯函数（断言逐行对照 ``service.py`` 真实实现写成）：

  - ``parse_accept_language`` / ``detect_language``   语言识别回退链
  - ``resolve_translation``                           词条回退链
  - ``progress_percentage`` / ``language_progress`` / ``bundle_stats``   进度与统计
  - ``missing_keys`` / ``untranslated_keys``          缺失 / 未翻译 diff
  - ``levenshtein_distance`` / ``similarity`` / ``match_memory``         记忆库打分
  - ``format_number`` / ``format_currency`` / ``format_relative_time``   本地化格式
  - ``localize`` / ``locale_public_view``             区域时间格式化
  - ``render_export`` / ``parse_import``              导入导出生成与解析（互为逆）
  - ``generate_template`` / ``summarize_memory`` / ``normalize_entry``
  - ``entry_value`` / ``entry_status`` / ``provider_status``

运行（在仓库根目录）::

    python -m pytest src/api/v3/modules/system/translation/_pending_test_translation.py -q

**本文件尚未运行**：本任务执行环境不允许跑 pytest，故仅静态编写。
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.modules.system.translation.service import (
    bundle_stats,
    detect_language,
    entry_status,
    entry_value,
    flatten_keys,
    format_currency,
    format_number,
    format_relative_time,
    generate_template,
    language_progress,
    levenshtein_distance,
    localize,
    locale_public_view,
    match_memory,
    missing_keys,
    normalize_entry,
    parse_accept_language,
    parse_import,
    progress_percentage,
    provider_status,
    render_export,
    resolve_translation,
    similarity,
    summarize_memory,
    untranslated_keys,
)

SUPPORTED = ["en", "zh-CN", "zh-TW"]


# ================================================================== 语言识别
def test_parse_accept_language_order_by_q():
    parsed = parse_accept_language("zh-CN,zh;q=0.9,en;q=0.8")
    assert parsed == [("zh-CN", 1.0), ("zh", 0.9), ("en", 0.8)]


def test_detect_language_exact_and_main_fallback():
    assert detect_language("zh-CN,zh;q=0.9,en;q=0.8", SUPPORTED, "en") == "zh-CN"
    assert detect_language("zh-TW", SUPPORTED, "en") == "zh-TW"
    # zh 未精确命中 → 主语言匹配到列表里第一个 zh*
    assert detect_language("zh", SUPPORTED, "en") == "zh-CN"
    # 完全不支持 → 默认语言
    assert detect_language("fr-FR,fr;q=0.9", SUPPORTED, "en") == "en"
    assert detect_language(None, SUPPORTED, "en") == "en"
    assert detect_language("", SUPPORTED, "en") == "en"


def test_detect_language_respects_q_weight_and_zero():
    # q 权重决定优先级：zh-CN 优先于排在前面的 en
    assert detect_language("en;q=0.5,zh-CN;q=0.9", SUPPORTED, "en") == "zh-CN"
    # q=0 视为不可接受，跳过
    assert detect_language("zh-CN;q=0,en", SUPPORTED, "en") == "en"


# ================================================================== 词条回退链
def _sample_bundles():
    return {
        "en": {"a": {"value": "A"}, "b": {"value": "B"}},
        "zh-CN": {"a": {"value": "甲"}},
    }


def test_resolve_translation_layers():
    bundles = _sample_bundles()
    assert resolve_translation(bundles, "a", "zh-CN", "en") == {"value": "甲", "source": "zh-CN"}
    assert resolve_translation(bundles, "b", "zh-CN", "en") == {"value": "B", "source": "en"}
    assert resolve_translation(bundles, "c", "zh-CN", "en") == {"value": "c", "source": "default"}
    assert resolve_translation(bundles, "c", "zh-CN", "en", default="X") == {"value": "X", "source": "default"}


def test_resolve_translation_empty_value_falls_back():
    bundles = {"en": {"a": {"value": "A"}}, "zh-CN": {"a": {"value": ""}}}
    assert resolve_translation(bundles, "a", "zh-CN", "en") == {"value": "A", "source": "en"}


# ================================================================== 进度 / 统计
def test_progress_percentage():
    assert progress_percentage(0, 0) == 0.0
    assert progress_percentage(1, 4) == 25.0
    assert progress_percentage(3, 3) == 100.0


def test_language_progress_counts_and_diff():
    bundles = {
        "en": {"a": {"value": "A", "status": "translated"}, "b": {"value": "B", "status": "translated"}},
        "zh-CN": {"a": {"value": "甲", "status": "translated"}, "b": {"value": "", "status": "pending"}},
    }
    progress = language_progress(bundles, "zh-CN", "en")
    assert progress["total_keys"] == 2
    assert progress["present_keys"] == 2
    assert progress["translated"] == 1
    assert progress["pending"] == 1
    assert progress["reviewed"] == 0
    assert progress["completion_rate"] == 50.0
    assert progress["missing_count"] == 0
    assert progress["untranslated_keys"] == ["b"]
    assert progress["untranslated_count"] == 1
    assert progress["last_updated"] is None


def test_language_progress_missing_keys():
    bundles = {
        "en": {"a": {"value": "A"}, "b": {"value": "B"}},
        "zh-TW": {"a": {"value": "甲"}},
    }
    progress = language_progress(bundles, "zh-TW", "en")
    assert progress["missing_keys"] == ["b"]
    assert progress["missing_count"] == 1
    assert progress["completion_rate"] == 50.0


def test_bundle_stats_relative_to_source():
    bundles = {
        "en": {"a": {"value": "A"}, "b": {"value": "B"}},
        "zh-CN": {"a": {"value": "甲"}},
    }
    stats = bundle_stats(bundles, ["en", "zh-CN"], "en")
    assert stats["source_language"] == "en"
    assert stats["source_keys"] == 2
    assert stats["languages"]["en"]["completion_rate"] == 100.0
    assert stats["languages"]["zh-CN"]["completion_rate"] == 50.0
    assert stats["languages"]["zh-CN"]["missing_keys"] == 1


def test_missing_and_untranslated():
    bundles = {
        "en": {"a": {"value": "A"}, "b": {"value": "B"}},
        "zh-CN": {"a": {"value": ""}},
    }
    assert missing_keys(bundles, "zh-CN", "en") == ["b"]
    assert untranslated_keys(bundles, "zh-CN", "en") == ["a", "b"]


# ================================================================== 记忆库打分
def test_levenshtein_and_similarity():
    assert levenshtein_distance("kitten", "sitting") == 3
    assert similarity("abc", "abc") == 1.0
    assert similarity("", "x") == 0.0
    # 4 长、距离 1 → 1 - 1/4 = 0.75
    assert similarity("abcd", "abce") == pytest.approx(0.75)


def test_match_memory_exact_and_fuzzy():
    entries = [
        {"source": "Hello world", "target": "你好世界"},
        {"source": "Hello word", "target": "你好词"},
        {"source": "Goodbye", "target": "再见"},
    ]
    matched = match_memory(entries, "Hello world", threshold=0.7, limit=10)
    assert len(matched) == 2
    assert matched[0]["match_type"] == "exact"
    assert matched[0]["similarity"] == 1.0
    assert matched[0]["target"] == "你好世界"
    assert matched[1]["match_type"] == "fuzzy"
    # "world"→"word" 距离 1，长度 11 → 0.9091
    assert matched[1]["similarity"] == pytest.approx(0.9091)


def test_match_memory_threshold_and_limit():
    entries = [
        {"source": "Hello world", "target": "a"},
        {"source": "Hello word", "target": "b"},
    ]
    assert len(match_memory(entries, "Hello world", threshold=0.95)) == 1
    assert len(match_memory(entries, "Hello world", threshold=0.0, limit=1)) == 1


def test_summarize_memory():
    memory = {
        "en_zh-CN": [{"source": "a"}, {"source": "b"}],
        "en_ja": [{"source": "c"}],
    }
    stats = summarize_memory(memory)
    assert stats["total_entries"] == 3
    assert stats["language_pairs"] == 2
    assert stats["pairs_detail"][0]["pair"] == "en_zh-CN"
    assert stats["pairs_detail"][0]["source_lang"] == "en"
    assert stats["pairs_detail"][0]["target_lang"] == "zh-CN"
    assert stats["pairs_detail"][0]["entry_count"] == 2


# ================================================================== 本地化格式
def test_format_number():
    assert format_number(1234567.5, {"thousands": ",", "decimal": "."}, 2) == "1,234,567.50"
    assert format_number(1234.5, {"thousands": ".", "decimal": ","}, 2) == "1.234,50"
    assert format_number(-1234, {"thousands": ",", "decimal": "."}, 0) == "-1,234"
    assert format_number(0, {"thousands": ",", "decimal": "."}, 2) == "0.00"


def test_format_currency():
    assert format_currency(1234.5, "en-US")["text"] == "$1,234.50"
    assert format_currency(1234.5, "zh-CN")["text"] == "¥1,234.50"
    assert format_currency(1000, "zh-TW")["text"] == "1,000.00 NT$"
    assert format_currency(1000, "ru-RU")["text"] == "1 000,00 ₽"


def test_format_relative_time():
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert format_relative_time(now.replace(second=30), "en-US", now=now) == "just now"
    five_minutes_ago = now - timedelta(minutes=5)
    assert format_relative_time(five_minutes_ago, "en-US", now=now) == "5 minute ago"
    assert format_relative_time(five_minutes_ago, "zh-CN", now=now) == "5分钟前"


def test_localize_and_locale_view():
    dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = localize(dt, "zh-CN")
    assert result["timezone"] == "Asia/Shanghai"
    assert result["date"] == "2024年06月15日"
    assert result["time"] == "20:00:00"
    assert isinstance(result["relative"], str)

    view = locale_public_view("zh-CN")
    assert view["timezone"] == "Asia/Shanghai"
    assert view["currency"]["code"] == "CNY"
    assert view["currency"]["symbol"] == "¥"
    assert view["currency"]["position"] == "before"
    assert view["first_day_of_week"] == 1

    with pytest.raises(NotFoundError):
        locale_public_view("xx-XX")


# ================================================================== 导入导出
def test_render_export_json_and_parse_roundtrip():
    content, media = render_export("zh-CN", {"a": "甲", "b": "乙"}, "json")
    assert media == "application/json"
    text = content.decode("utf-8")
    parsed = parse_import(text, "json")
    assert parsed["language"] == "zh-CN"
    assert parsed["translations"] == {"a": "甲", "b": "乙"}


def test_render_export_csv_bom_and_header():
    content, media = render_export("zh-CN", {"b": "乙", "a": "甲"}, "csv")
    assert media.startswith("text/csv")
    text = content.decode("utf-8")
    assert text.startswith("\ufeff")  # UTF-8 BOM
    assert "键" in text and "译文" in text
    # 行按 key 排序
    assert text.index("a,甲") < text.index("b,乙")
    parsed = parse_import(text, "csv")
    assert parsed["translations"] == {"a": "甲", "b": "乙"}


def test_render_export_po_and_parse():
    content, media = render_export("zh-CN", {"a": "甲"}, "po")
    assert media.startswith("text/x-gettext-translation")
    text = content.decode("utf-8")
    assert 'msgid "a"' in text
    assert 'msgstr "甲"' in text
    assert parse_import(text, "po")["translations"] == {"a": "甲"}


def test_render_export_xliff_and_parse():
    content, media = render_export("zh-CN", {"a": "甲"}, "xliff")
    assert media.startswith("application/xliff+xml")
    text = content.decode("utf-8")
    assert "trans-unit" in text
    assert parse_import(text, "xliff")["translations"] == {"a": "甲"}


def test_render_and_parse_reject_unknown_format():
    with pytest.raises(BadRequestError):
        render_export("zh-CN", {}, "toml")
    with pytest.raises(BadRequestError):
        parse_import("{}", "toml")


def test_parse_import_json_invalid_raises():
    with pytest.raises(BadRequestError):
        parse_import("{not json", "json")


# ================================================================== 其它纯函数
def test_generate_template():
    bundles = {"en": {"a": {"value": "A"}, "b": {"value": "B"}}, "zh-CN": {"a": {"value": "甲"}}}
    assert generate_template(bundles, "zh-CN", "en") == {"a": "甲", "b": ""}


def test_flatten_keys():
    assert flatten_keys({"a": {"b": "1"}, "c": "2"}) == ["a.b", "c"]


def test_entry_value_and_status():
    assert entry_value(None) == ""
    assert entry_value({"value": "x"}) == "x"
    assert entry_value("raw") == "raw"
    assert entry_status({"value": "x", "status": "pending"}) == "pending"
    assert entry_status({"value": "x"}) == "translated"
    assert entry_status({"value": ""}) == "pending"
    assert entry_status({"value": "x", "status": "bogus"}) == "translated"


def test_normalize_entry():
    entry = normalize_entry("x")
    assert entry["value"] == "x"
    assert entry["status"] == "translated"
    assert set(entry) == {"value", "status", "translator_id", "translator_name", "updated_at"}
    assert normalize_entry("")["status"] == "pending"


def test_provider_status():
    status = provider_status("baidu")
    assert status["provider"] == "baidu"
    assert status["name"] == "百度翻译"
    assert status["required_env"] == ["BAIDU_TRANSLATE_APP_ID", "BAIDU_TRANSLATE_SECRET_KEY"]
    assert isinstance(status["available"], bool)
    with pytest.raises(BadRequestError):
        provider_status("nope")
