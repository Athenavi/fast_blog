"""analytics/seo（纯函数 / 内容助手 / JSON-LD）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import json
import pytest
from fastapi import FastAPI
from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.ai.workflow import tasks
from src.api.v3.modules.analytics.seo.assistant_service import (
    GENERATE_TASK_TYPE,
    SEO_FIELDS,
    normalize_keywords,
    parse_llm_json,
)
from src.api.v3.modules.analytics.seo.schema_org import (
    SCHEMA_TYPES,
    SchemaOrgService,
    schema_org_service,
)
from src.api.v3.modules.analytics.seo.service import (
    is_internal_href,
    parse_content_structure,
    resolve_article_id,
)


# ============================================================ 来自 test_v3_seo_helpers.py（6 项）
def test_parse_content_structure_uses_bs4():
    html = (
        '<h1>主标题</h1><h2>小标题</h2>'
        '<img src="/media/a.png" alt="图">'
        '<a href="/articles/12">内链</a>'
        '<a href="https://example.com/x">外链</a>'
    )
    structure = parse_content_structure(html)

    assert structure["headings"]["h1"] == ["主标题"]
    assert structure["headings"]["h2"] == ["小标题"]
    assert structure["images"][0]["src"] == "/media/a.png"
    assert structure["images"][0]["alt"] == "图"
    assert "/articles/12" in structure["hrefs"]
    assert "https://example.com/x" in structure["hrefs"]


def test_parse_content_structure_empty_input():
    structure = parse_content_structure("")
    assert structure["headings"] == {"h1": [], "h2": [], "h3": []}
    assert structure["images"] == []
    assert structure["hrefs"] == []


def test_is_internal_href():
    assert is_internal_href("/articles/1")
    assert is_internal_href("/p/hello-world")
    assert not is_internal_href("https://example.com/a")
    assert not is_internal_href("//cdn.example.com/a")  # 协议相对地址
    assert not is_internal_href("#anchor")
    assert not is_internal_href("mailto:a@b.com")
    assert not is_internal_href("")


def test_resolve_article_id_by_numeric_path():
    assert resolve_article_id("/articles/12", {}, {12}) == 12
    assert resolve_article_id("/articles/12.html", {}, {12}) == 12
    assert resolve_article_id("/article/12/", {}, {12}) == 12
    assert resolve_article_id("/p/12", {}, {12}) == 12
    # id 不在集合里 → 不认
    assert resolve_article_id("/articles/99", {}, {12}) is None


def test_resolve_article_id_by_slug():
    slug_map = {"hello-world": 5}
    assert resolve_article_id("/hello-world", slug_map, {5}) == 5
    assert resolve_article_id("/p/hello-world", slug_map, {5}) == 5
    assert resolve_article_id("/articles/hello-world", slug_map, {5}) == 5
    assert resolve_article_id("/unknown-slug", slug_map, {5}) is None


def test_resolve_article_id_ignores_external_and_query():
    assert resolve_article_id("https://example.com/articles/12", {}, {12}) is None
    assert resolve_article_id("/articles/12?utm=x#top", {}, {12}) == 12


# ============================================================ 来自 test_v3_seo_assistant.py（13 项）
BASE = "/api/v3/analytics/seo"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ JSON 容错解析
def test_parse_llm_json_plain_object():
    assert parse_llm_json('{"seo_title": "标题"}') == {"seo_title": "标题"}


def test_parse_llm_json_strips_code_fence():
    text = '```json\n{"seo_title": "标题", "seo_keywords": ["a", "b"]}\n```'

    assert parse_llm_json(text)["seo_keywords"] == ["a", "b"]


def test_parse_llm_json_with_surrounding_prose():
    text = '好的，结果如下：\n{"seo_title": "标题"}\n希望有帮助。'

    assert parse_llm_json(text) == {"seo_title": "标题"}


def test_parse_llm_json_array():
    assert parse_llm_json('["标题一", "标题二"]') == ["标题一", "标题二"]


@pytest.mark.parametrize("bad", ["", "   ", "没有 JSON 的纯文本"])
def test_parse_llm_json_raises_on_unparsable(bad):
    with pytest.raises(BadRequestError):
        parse_llm_json(bad)


# ------------------------------------------------------------------ 关键词归一
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (["a", "b", "c"], "a,b,c"),
        ("a, b ,c", "a, b ,c"),
        ([], None),
        (None, None),
        ("", None),
        ([" ", "x"], "x"),
    ],
)
def test_normalize_keywords(raw, expected):
    assert normalize_keywords(raw) == expected


def test_normalize_keywords_truncates_to_column_width():
    result = normalize_keywords(["x" * 300])

    assert result is not None and len(result) <= 255


# ------------------------------------------------------------------ 创作辅助任务类型
def test_writing_assistant_task_types_registered():
    """对齐 v2 AIWritingAssistantService 的六项能力（摘要复用既有 summarize）"""
    for task_type in ("polish", "grammar_check", "smart_continue", "style_transform", "generate_titles"):
        assert task_type in tasks.TASK_TEMPLATES, task_type


def test_seo_generate_task_type_registered_and_renders():
    assert GENERATE_TASK_TYPE in tasks.TASK_TEMPLATES

    system, prompt = tasks.render(GENERATE_TASK_TYPE, input_text="标题：测试")

    assert "JSON" in system
    assert "seo_title" in prompt
    assert "标题：测试" in prompt


def test_catalogue_covers_all_templates():
    catalogue = {item["task_type"] for item in tasks.catalogue()}

    assert catalogue == set(tasks.TASK_TEMPLATES)


def test_style_transform_uses_target_lang_slot():
    _system, prompt = tasks.render("style_transform", input_text="正文", target_lang="轻松")

    assert "轻松" in prompt


# ------------------------------------------------------------------ 字段与端点
def test_seo_fields_match_article_seo_columns():
    from shared.models.article.article_seo import ArticleSEO

    columns = set(ArticleSEO.__table__.columns.keys())

    assert set(SEO_FIELDS) <= columns


def test_analyze_endpoint_still_works_shape():
    """既有 /analyze 端点没被新端点影响（静态路径仍在参数路径之前注册）"""
    paths = [route.path for route in _app().routes]

    assert paths.index(f"{BASE}/analyze") < paths.index(f"{BASE}/articles/{{article_id}}")


# ============================================================ 来自 test_v3_seo_schema_org.py（10 项）
BASE__seo_schema_org = "/api/v3/analytics/seo"


def _app__seo_schema_org() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 类型映射
def test_every_schema_type_maps_to_a_real_generator_method():
    generator = SchemaOrgService()._generator

    for schema_type in SCHEMA_TYPES:
        suffix = SchemaOrgService._method_suffix(schema_type)
        assert hasattr(generator, f"generate_{suffix}_schema"), schema_type


def test_types_listing_shape():
    items = schema_org_service.types()

    assert {item["type"] for item in items} == set(SCHEMA_TYPES)
    assert all(item["label"] for item in items)


# ------------------------------------------------------------------ 生成
def test_build_article_schema_returns_json_ld():
    schema = schema_org_service.build(
        "Article",
        title="标题",
        description="描述",
        url="https://example.com/article/x",
        author_name="作者",
    )

    assert schema["@context"] == "https://schema.org"
    assert schema["@type"] == "Article"
    assert schema["headline"] == "标题"
    assert schema["author"]["name"] == "作者"


def test_build_rejects_unknown_type():
    with pytest.raises(BadRequestError):
        schema_org_service.build("NotAType")


def test_build_reports_bad_params_as_400():
    # 缺必填参数（author_name）→ 400，而不是 500
    with pytest.raises(BadRequestError):
        schema_org_service.build("Article", title="t", description="d", url="u")


def test_build_breadcrumb_and_faq():
    breadcrumb = schema_org_service.build(
        "BreadcrumbList", items=[{"name": "首页", "url": "https://example.com/"}]
    )
    faq = schema_org_service.build(
        "FAQPage", questions=[{"question": "Q1", "answer": "A1"}]
    )

    assert breadcrumb["@type"] == "BreadcrumbList"
    assert faq["@type"] == "FAQPage"


def test_to_json_ld_and_script_tag_are_valid():
    schema = schema_org_service.build(
        "Person", name="张三", url="https://example.com/author/1", description="作者简介"
    )

    json_ld = schema_org_service.to_json_ld(schema)
    assert json.loads(json_ld)["name"] == "张三"

    tag = schema_org_service.to_script_tag(schema)
    assert "application/ld+json" in tag
    assert '"name"' in tag


# ------------------------------------------------------------------ 面包屑
def test_breadcrumb_items_without_category():
    items = SchemaOrgService._breadcrumb_items(
        base="https://example.com",
        category_name="",
        category_slug="",
        article_title="文章",
        article_slug="hello",
    )

    assert [item["name"] for item in items] == ["首页", "文章"]
    assert items[-1]["url"] == "https://example.com/article/hello"


def test_breadcrumb_items_with_category_and_empty_base():
    items = SchemaOrgService._breadcrumb_items(
        base="",
        category_name="技术",
        category_slug="tech",
        article_title="文章",
        article_slug="hello",
    )

    assert [item["name"] for item in items] == ["首页", "技术", "文章"]
    assert items[0]["url"] == "/"
    assert items[1]["url"] == ""


# ------------------------------------------------------------------ 站点覆盖
def test_apply_site_overrides_publisher_name_and_logo():
    schema = schema_org_service.build(
        "Article",
        title="t",
        description="d",
        url="https://example.com/a",
        author_name="a",
    )
    SchemaOrgService._apply_site(
        [schema], {"name": "我的站点", "base_url": "https://x.com", "logo": "https://x.com/logo.png"}
    )

    assert schema["publisher"]["name"] == "我的站点"
    assert schema["publisher"]["logo"]["url"] == "https://x.com/logo.png"

# ------------------------------------------------------------------ 端点
