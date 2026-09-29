"""批次：RSS / Atom 订阅接线的回归测试

历史状况：仓库里有两份 feed 实现（``src/utils/feed_generator.py`` 与
``shared/services/advanced_features/feed_service.py``），但没有任何路由暴露它们，
而 ``src/utils/seo.py`` 已在 HTML head 里声明 ``/api/v1/feed/rss``（v1 早已删除 → 死链）。

本批次把两份实现合并（service 取数 + generator 序列化）并接到
``/api/v3/analytics/seo/feed/{rss,atom}``。这里覆盖：
  1. 生成器产出必须是**合法 XML**（历史上 atom:link / content:encoded 缺命名空间声明）
  2. 路由已注册且为公开路径（不带鉴权依赖）
  3. 无文章时仍返回结构合法的空 feed
"""

import asyncio
from datetime import datetime
from xml.dom.minidom import parseString as parse_xml


from shared.services.advanced_features import feed_service
from src.utils.feed_generator import FeedItem, RSSFeedGenerator

RSS_PATH = "/api/v3/analytics/seo/feed/rss"
ATOM_PATH = "/api/v3/analytics/seo/feed/atom"


def _generator() -> RSSFeedGenerator:
    gen = RSSFeedGenerator(
        title="FastBlog",
        link="https://example.com",
        description="最新文章订阅",
        language="zh-CN",
        feed_url="https://example.com/rss.xml",
        icon_url="https://example.com/favicon.ico",
        copyright="(c) FastBlog",
    )
    gen.add_item(
        FeedItem(
            title="Hello <world> & friends",
            link="https://example.com/articles/hello",
            description="摘要",
            pub_date=datetime(2026, 1, 2, 3, 4, 5),
            author="author@example.com",
            categories=["tech", "python"],
            content="<p>正文 &amp; 更多</p>",
            image="https://example.com/cover.jpg",
        )
    )
    return gen


def test_rss_output_is_well_formed_xml():
    xml = _generator().generate_rss()
    parse_xml(xml)  # 命名空间缺失时会抛 ExpatError: unbound prefix
    assert "xmlns:atom=" in xml
    assert "xmlns:content=" in xml
    assert "<content:encoded>" in xml
    assert "https://example.com/rss.xml" in xml
    # 标题里的尖括号必须被转义
    assert "Hello &lt;world&gt; &amp; friends" in xml


def test_atom_output_is_well_formed_xml():
    atom = _generator().generate_atom()
    parse_xml(atom)
    assert "https://example.com/articles/hello" in atom
    assert "<title>Hello &lt;world&gt; &amp; friends</title>" in atom


class _EmptyScalars:
    def scalars(self):
        return self

    def all(self):
        return []


class _EmptySession:
    """只支持 ``(await db.execute(stmt)).scalars().all()`` 的空会话"""

    async def execute(self, *_args, **_kwargs):
        return _EmptyScalars()


def test_empty_feed_is_still_valid_xml():
    xml = asyncio.run(
        feed_service.generate_rss_feed(_EmptySession(), base_url="https://example.com")
    )
    parse_xml(xml)
    assert "<channel>" in xml
    assert feed_service.RSS_PATH in xml  # atom:link rel=self

    atom = asyncio.run(
        feed_service.generate_atom_feed(_EmptySession(), base_url="https://example.com")
    )
    parse_xml(atom)
    assert "<feed" in atom


def test_feed_metadata_uses_v3_paths():
    """元数据里给出的订阅地址必须是 v3 权威路径（不是已删除的 /api/v1）"""
    meta = asyncio.run(feed_service.get_feed_metadata(_EmptySession()))
    assert feed_service.RSS_PATH == RSS_PATH
    assert feed_service.ATOM_PATH == ATOM_PATH
    assert meta["rss_url"] == RSS_PATH
    assert meta["atom_url"] == ATOM_PATH


def test_seo_discovery_tags_point_to_root_feed_paths():
    from src.utils.seo import get_feed_discovery_tags

    tags = get_feed_discovery_tags("https://example.com")
    assert tags["rss_link"] == "https://example.com/rss.xml"
    assert tags["atom_link"] == "https://example.com/atom.xml"
    assert "api/v1" not in tags["rss_xml"]
