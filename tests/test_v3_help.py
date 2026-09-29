"""测试：帮助系统（纯函数 + 服务层）

不需要数据库：

  - ``DEFAULT_TOPICS`` / ``DEFAULT_TOOLTIPS`` / ``DEFAULT_VIDEOS`` 是内置常量
  - ``_strip_html`` / ``_extract_excerpt`` / ``_score_topic`` / ``_search_topics`` /
    ``_merge_topics`` / ``_lookup_tooltip`` 是纯函数（打分的排序、摘要提取、合并覆盖）
  - ``help_service.videos`` 是静态方法

真实持久化（``system_settings`` 的 ``help.topics``）与路由注册走运行时验证。
"""

from src.api.v3.modules.system.help.service import (
    DEFAULT_TOPICS,
    DEFAULT_TOOLTIPS,
    DEFAULT_VIDEOS,
    STORAGE_KEY,
    _extract_excerpt,
    _lookup_tooltip,
    _merge_topics,
    _score_topic,
    _search_topics,
    _strip_html,
    help_service,
)

# v2 ``DEFAULT_HELP_CONTENT`` 的全部条目（必须完整保留）
V2_PAGE_KEYS = {
    "admin_dashboard",
    "article_editor",
    "media_library",
    "theme_settings",
    "plugin_manager",
    "user_management",
}


# ------------------------------------------------------------------ 默认主题
def test_storage_key_constant():
    assert STORAGE_KEY == "help.topics"


def test_default_topics_keep_every_v2_entry():
    keys = {topic["page_key"] for topic in DEFAULT_TOPICS}

    assert keys == V2_PAGE_KEYS


def test_default_topics_are_well_formed():
    for topic in DEFAULT_TOPICS:
        assert {"page_key", "title", "content", "tags", "language"} <= set(topic)
        assert topic["page_key"]
        assert topic["title"]
        assert topic["content"]
        assert isinstance(topic["tags"], list) and topic["tags"]
        assert topic["language"] == "zh_CN"


def test_default_topic_page_keys_are_unique():
    keys = [topic["page_key"] for topic in DEFAULT_TOPICS]

    assert len(keys) == len(set(keys))


# ------------------------------------------------------------------ 纯文本 / 摘要
def test_strip_html_removes_tags_and_collapses_whitespace():
    text = _strip_html("<h3>标题</h3>\n  <p>正文   内容</p>")

    assert "<" not in text
    assert text == "标题 正文 内容"


def test_extract_excerpt_returns_text_when_short():
    assert _extract_excerpt("<p>很短</p>", "很短") == "很短"


def test_extract_excerpt_centres_on_hit_not_head():
    content = "前" * 300 + "关键词" + "后" * 300

    excerpt = _extract_excerpt(content, "关键词")

    assert "关键词" in excerpt
    assert excerpt.startswith("...")
    assert excerpt.endswith("...")
    # 绝不是简单截头：命中词不应出现在开头的纯正文里
    assert excerpt.index("关键词") > 3


def test_extract_excerpt_falls_back_to_head_when_missing():
    content = "甲" * 400

    excerpt = _extract_excerpt(content, "不存在")

    assert excerpt.startswith("甲" * 5)
    assert excerpt.endswith("...")


# ------------------------------------------------------------------ 打分
def test_score_prefers_title_hit_over_content_hit():
    title_hit = {"page_key": "a", "title": "主题检索", "content": "无关内容", "tags": []}
    content_hit = {"page_key": "b", "title": "标题在这里", "content": "这里提到主题检索一次", "tags": []}

    assert _score_topic(title_hit, "主题检索")["score"] > _score_topic(content_hit, "主题检索")["score"]


def test_score_gives_phrase_bonus_and_clamps_to_one():
    topic = {"page_key": "a", "title": "SEO 优化", "content": "SEO 优化 SEO 优化", "tags": ["SEO 优化"]}

    result = _score_topic(topic, "SEO 优化")

    assert result["score"] <= 1.0
    assert result["score"] >= 0.6  # 标题短语命中（0.55 + 0.10）以上
    assert set(result["matched_fields"]) == {"title", "tags", "content"}


def test_score_counts_repeated_hits():
    once = {"page_key": "a", "title": "x", "content": "关键词 只出现一次", "tags": []}
    many = {"page_key": "a", "title": "x", "content": "关键词 关键词 关键词 关键词", "tags": []}

    assert _score_topic(many, "关键词")["score"] > _score_topic(once, "关键词")["score"]


def test_score_zero_for_miss_and_empty_query():
    topic = {"page_key": "a", "title": "标题", "content": "内容", "tags": []}

    assert _score_topic(topic, "完全没有")["score"] == 0.0
    assert _score_topic(topic, "   ")["score"] == 0.0


def test_score_partial_multiword_hit():
    topic = {"page_key": "a", "title": "文章编辑器", "content": "编辑器相关说明，文章相关", "tags": []}

    result = _score_topic(topic, "文章 编辑器")

    assert result["score"] > 0
    assert "title" in result["matched_fields"]


# ------------------------------------------------------------------ 搜索（排序 / 摘要 / 字段）
def test_search_sorts_by_score_desc():
    results = _search_topics(DEFAULT_TOPICS, "SEO")

    assert results
    scores = [item["score"] for item in results]
    assert scores == sorted(scores, reverse=True)


def test_search_result_shape_and_excerpt():
    results = _search_topics(DEFAULT_TOPICS, "媒体库")

    assert results
    top = results[0]
    assert set(top) == {"page_key", "title", "excerpt", "score", "matched_fields"}
    assert top["page_key"] == "media_library"
    assert "媒体" in top["excerpt"]


def test_search_respects_limit_and_filters_misses():
    limited = _search_topics(DEFAULT_TOPICS, "文章", limit=1)
    miss = _search_topics(DEFAULT_TOPICS, "不存在的词xyz")

    assert len(limited) == 1
    assert miss == []


# ------------------------------------------------------------------ 合并（覆盖）
def test_merge_overrides_default_by_page_key():
    defaults = [{"page_key": "a", "title": "A"}, {"page_key": "b", "title": "B"}]
    custom = [{"page_key": "a", "title": "A2", "content": "覆盖"}]

    merged = _merge_topics(defaults, custom)

    assert [topic["title"] for topic in merged] == ["A2", "B"]
    assert len(merged) == 2


def test_merge_appends_new_custom_topics():
    defaults = [{"page_key": "a", "title": "A"}]
    custom = [{"page_key": "c", "title": "C"}]

    merged = _merge_topics(defaults, custom)

    assert [topic["page_key"] for topic in merged] == ["a", "c"]


def test_merge_normalizes_missing_fields():
    merged = _merge_topics([], [{"page_key": "x", "title": "X"}])

    assert merged[0]["tags"] == []
    assert merged[0]["language"] == "zh_CN"


# ------------------------------------------------------------------ 字段提示
def test_lookup_tooltip_context_and_fallback():
    assert "URL" in _lookup_tooltip("slug", "general")
    # 上下文专属命中与 general 兜底不同
    assert _lookup_tooltip("slug", "article_editor") != _lookup_tooltip("slug", "general")
    # 未知上下文退回 general
    assert _lookup_tooltip("slug", "no_such_context") == _lookup_tooltip("slug", "general")


def test_lookup_tooltip_miss_returns_none():
    assert _lookup_tooltip("not_a_field", "general") is None


def test_default_tooltips_cover_every_v2_field():
    v2_fields = {
        "slug",
        "excerpt",
        "featured_image",
        "tags",
        "status",
        "publish_date",
        "meta_title",
        "meta_description",
    }

    assert v2_fields <= set(DEFAULT_TOOLTIPS)


# ------------------------------------------------------------------ 视频
def test_videos_all_and_filtered():
    assert len(help_service.videos()) == len(DEFAULT_VIDEOS)
    assert [item["id"] for item in help_service.videos("seo")] == ["seo-optimization"]
    assert [item["id"] for item in help_service.videos("article_editor")] == ["writing-articles"]
    assert help_service.videos("不存在的主题") == []
