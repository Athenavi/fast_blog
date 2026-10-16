"""ops/migration（多格式 / WordPress WXR）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.v3 import register_v3_routes
from src.api.v3.modules.content.redirect.service import normalize_path
from src.api.v3.modules.ops.migration.importers import (
    IMPORTER_KINDS,
    as_datetime,
    as_list,
    as_status,
    load_feed,
    parse_csv,
    parse_ghost,
    parse_json,
    parse_markdown_path,
    pick,
    slugify,
    split_front_matter,
    to_html,
)
from src.api.v3.modules.ops.migration.service import SUPPORTED_IMPORTERS
from src.api.v3.modules.ops.migration.wxr_importer import (
    IMPORTABLE_POST_TYPES,
    STATUS_DELETED,
    STATUS_MAP,
    ImportStats,
    parse_wxr,
    parse_wxr_datetime,
)

# ============================================================ 来自 test_v3_migration_multiformat.py（19 项）
REDIRECT_BASE = "/api/v3/content/redirect"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 值归一化
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hello World", "hello-world"),
        ("中文 标题", "中文-标题"),
        ("a//b__c", "a-b__c"),
        ("  Spaces  ", "spaces"),
        ("", ""),
    ],
)
def test_slugify(raw, expected):
    assert slugify(raw) == expected


def test_as_list_handles_all_shapes():
    assert as_list("a, b;c") == ["a", "b", "c"]
    assert as_list(["a", "a", "b"]) == ["a", "b"]
    assert as_list([{"name": "标签"}, {"slug": "x"}]) == ["标签", "x"]
    assert as_list(None) == []


def test_as_datetime_accepts_common_forms():
    assert as_datetime("2024-03-05") == as_datetime("2024-03-05T00:00:00")
    assert as_datetime("2024-03-05T01:02:03Z").year == 2024
    assert as_datetime("Mon, 05 Mar 2024 01:02:03 +0000") is not None
    assert as_datetime(1700000000).year == 2023
    assert as_datetime(1700000000000).year == 2023
    assert as_datetime("") is None
    assert as_datetime("not-a-date") is None


def test_as_status_maps_words_and_booleans():
    assert as_status("published") == "published"
    assert as_status(True) == "published"
    assert as_status(False) == "draft"
    assert as_status(1) == "published"
    assert as_status("") == "draft"
    assert as_status("weird") is None


def test_pick_prefers_configured_field_map():
    record = {"title": "A", "headline": "B", "body": "<p>x</p>"}

    assert pick(record, "title") == "A"
    assert pick(record, "title", {"title": ["headline"]}) == "B"
    assert pick(record, "content") == "<p>x</p>"
    assert pick(record, "slug") is None


# ------------------------------------------------------------------ 正文
def test_to_html_renders_markdown_and_keeps_html():
    assert "<h1>" in to_html("# 标题")
    assert to_html("<p>已渲染</p>") == "<p>已渲染</p>"
    # 原始 HTML 片段被转义（防导入带来的存储型 XSS）
    assert "<script>" not in to_html("<script>alert(1)</script>")


# ------------------------------------------------------------------ Markdown
def test_split_front_matter_parses_yaml_block():
    meta, body = split_front_matter("---\ntitle: 你好\npublished: false\n---\n正文")

    assert meta == {"title": "你好", "published": False}
    assert body == "正文"


def test_split_front_matter_without_block():
    meta, body = split_front_matter("# 标题\n正文")

    assert meta == {}
    assert body == "# 标题\n正文"


def test_parse_markdown_directory(tmp_path):
    (tmp_path / "a.md").write_text(
        "---\ntitle: 第一\nslug: first\ndate: 2024-01-02\ntags: [x, y]\nurl: https://old.site/2024/first\n---\n# 第一\n正文",
        encoding="utf-8",
    )
    (tmp_path / "b.md").write_text("# 第二篇\n正文", encoding="utf-8")
    (tmp_path / "skip.txt").write_text("忽略", encoding="utf-8")

    feed = parse_markdown_path(tmp_path)

    assert len(feed.items) == 2
    first = next(item for item in feed.items if item.slug == "first")
    assert first.title == "第一"
    assert first.status == "published"
    assert first.tags == ["x", "y"]
    assert first.source_url == "https://old.site/2024/first"
    assert "<h1>" in first.content

    second = next(item for item in feed.items if item.title == "第二篇")
    # 无 front matter → slug 由文件名派生（静态站点生成器里 URL 由文件名决定）
    assert second.slug == "b"
    assert second.source_url is None


def test_load_feed_dispatches_markdown_file(tmp_path):
    path = tmp_path / "one.md"
    path.write_text("---\ntitle: 单文件\n---\n内容", encoding="utf-8")

    feed = load_feed("markdown", path, {})

    assert len(feed.items) == 1
    assert feed.items[0].title == "单文件"


# ------------------------------------------------------------------ Ghost / JSON / CSV
def test_parse_ghost_import_export_shape():
    payload = {
        "db": [
            {
                "data": {
                    "posts": [
                        {
                            "id": "p1",
                            "title": "Ghost 文章",
                            "slug": "ghost-post",
                            "html": "<p>hi</p>",
                            "status": "published",
                            "published_at": "2024-05-06T07:08:09.000Z",
                            "url": "https://ghost.site/ghost-post/",
                        },
                        {"id": "p2", "title": "", "slug": "empty"},
                    ],
                    "tags": [{"id": "t1", "name": "随笔"}],
                    "posts_tags": [{"post_id": "p1", "tag_id": "t1"}],
                }
            }
        ]
    }

    feed = parse_ghost(json.dumps(payload))

    assert len(feed.items) == 1
    item = feed.items[0]
    assert item.title == "Ghost 文章"
    assert item.tags == ["随笔"]
    assert item.content == "<p>hi</p>"
    assert item.created_at is not None
    assert item.source_url == "https://ghost.site/ghost-post/"


def test_parse_json_flat_and_nested():
    flat = parse_json(json.dumps([{"title": "A", "markdown": "# A"}]), {})
    nested = parse_json(json.dumps({"articles": [{"headline": "B", "body": "<p>B</p>"}]}), {})

    assert flat.items[0].content.startswith("<h1>")
    assert nested.items[0].title == "B"


def test_parse_json_honours_field_map_and_default_status():
    feed = parse_json(
        json.dumps([{"t": "自定义字段", "c": "正文"}]),
        {"field_map": {"title": ["t"], "content": ["c"]}, "default_status": "published"},
    )

    item = feed.items[0]
    assert item.title == "自定义字段"
    assert item.status == "published"


def test_parse_csv_with_header_mapping():
    raw = "title,slug,body,tags,status\nCSV 文章,csv-post,正文,\"a,b\",draft\n"

    feed = parse_csv(raw, {})

    assert len(feed.items) == 1
    item = feed.items[0]
    assert item.slug == "csv-post"
    assert item.tags == ["a", "b"]
    assert item.status == "draft"


def test_parse_json_rejects_unknown_shape():
    with pytest.raises(ValueError):
        parse_json(json.dumps("just-a-string"), {})


# ------------------------------------------------------------------ 分派一致性
def test_supported_importers_cover_all_importer_kinds():
    assert set(IMPORTER_KINDS) <= SUPPORTED_IMPORTERS
    assert "wordpress" in SUPPORTED_IMPORTERS


def test_markdown_aliases_share_one_parser():
    assert {IMPORTER_KINDS["jekyll"], IMPORTER_KINDS["hexo"], IMPORTER_KINDS["hugo"]} == {"markdown"}


# ------------------------------------------------------------------ 跳转路径归一
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://old.example.com/2020/hello/?utm=1", "/2020/hello"),
        ("http://old.example.com", "/"),
        ("2020/hello", "/2020/hello"),
        ("/a//b/", "/a/b"),
        ("/", "/"),
        ("", ""),
    ],
)
def test_normalize_path(raw, expected):
    assert normalize_path(raw) == expected


# ------------------------------------------------------------------ 端点


def test_redirect_management_requires_auth_but_resolve_is_public():
    client = TestClient(_app())

    assert client.get(REDIRECT_BASE).status_code in (401, 403)
    assert client.post(REDIRECT_BASE, json={"from_path": "/a", "to_path": "/b"}).status_code in (401, 403)
    # 公开端点：缺参数应 422（schema 错误），而不是 401/403
    assert client.get(f"{REDIRECT_BASE}/resolve").status_code == 422


# ============================================================ 来自 test_v3_migration_wxr.py（7 项）
SAMPLE = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"
     xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:wp="http://wordpress.org/export/1.2/">
  <channel>
    <title>demo blog</title>
    <wp:wxr_version>1.2</wp:wxr_version>
    <wp:category>
      <wp:category_nicename>tech</wp:category_nicename>
      <wp:cat_name><![CDATA[技术]]></wp:cat_name>
    </wp:category>
    <item>
      <title>Hello</title>
      <dc:creator><![CDATA[admin]]></dc:creator>
      <content:encoded><![CDATA[<p>body</p>]]></content:encoded>
      <excerpt:encoded><![CDATA[summary]]></excerpt:encoded>
      <wp:post_id>11</wp:post_id>
      <wp:post_date><![CDATA[2024-01-02 03:04:05]]></wp:post_date>
      <wp:post_name><![CDATA[hello]]></wp:post_name>
      <wp:status><![CDATA[publish]]></wp:status>
      <wp:post_type><![CDATA[post]]></wp:post_type>
      <category domain="category" nicename="tech"><![CDATA[技术]]></category>
      <category domain="post_tag" nicename="tag-a"><![CDATA[标签甲]]></category>
    </item>
    <item>
      <title>Draft Post</title>
      <wp:post_id>12</wp:post_id>
      <wp:post_name><![CDATA[draft-post]]></wp:post_name>
      <wp:status><![CDATA[pending]]></wp:status>
      <wp:post_type><![CDATA[post]]></wp:post_type>
    </item>
    <item>
      <title>A Page</title>
      <wp:post_id>13</wp:post_id>
      <wp:post_name><![CDATA[a-page]]></wp:post_name>
      <wp:status><![CDATA[publish]]></wp:status>
      <wp:post_type><![CDATA[page]]></wp:post_type>
    </item>
  </channel>
</rss>
"""


def test_parse_feed_metadata_and_items():
    feed = parse_wxr(SAMPLE)

    assert feed.version == "1.2"
    assert feed.title == "demo blog"
    assert [c.name for c in feed.categories] == ["技术"]
    assert [item.post_type for item in feed.items] == ["post", "post", "page"]
    # 只有 post 可导入（page 会被跳过并写日志）
    assert len(feed.importable_items) == 2
    assert IMPORTABLE_POST_TYPES == {"post"}


def test_parse_item_fields():
    item = parse_wxr(SAMPLE).items[0]

    assert item.post_id == "11"
    assert item.title == "Hello"
    assert item.slug == "hello"
    assert item.status == "publish"
    assert item.creator == "admin"
    assert item.post_date == "2024-01-02 03:04:05"
    assert "<p>body</p>" in item.content
    assert item.excerpt == "summary"
    assert item.names_for("category") == ["技术"]
    assert item.names_for("post_tag") == ["标签甲"]
    assert item.slugs_for("category") == ["tech"]


def test_parse_rejects_broken_xml():
    with pytest.raises(ValueError):
        parse_wxr("<rss><channel>")


def test_parse_rejects_non_wxr_document():
    """合法 XML 但不是 WXR（没有 channel）必须报错，而不是当成空 feed 静默通过"""
    with pytest.raises(ValueError):
        parse_wxr("<note><to>a</to></note>")


def test_status_mapping():
    assert STATUS_MAP == {"publish": 1, "draft": 0}
    # 未列出的状态（pending/private/trash…）由导入器按草稿处理并写日志
    assert STATUS_MAP.get("pending") is None
    assert STATUS_DELETED == -1


def test_parse_wxr_datetime_formats():
    assert parse_wxr_datetime("2024-01-02 03:04:05").isoformat() == "2024-01-02T03:04:05"
    assert parse_wxr_datetime("Mon, 01 Jan 2024 10:00:00 +0000").year == 2024
    assert parse_wxr_datetime(None) is None
    assert parse_wxr_datetime("not a date") is None


def test_import_stats_progress():
    assert ImportStats(total=0).progress() == 100
    stats = ImportStats(total=4, imported=1, skipped=1)
    assert stats.handled == 2
    assert stats.progress() == 50
    stats.imported = 4
    assert stats.progress() == 100
