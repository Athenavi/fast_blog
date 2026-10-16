"""测试：无障碍（任务 14b）

不需要数据库：

  - ``validate`` 是**按元素解析**的规则集（v2 只有 4 条整篇子串判断，v3 换掉）
  - ``css`` / ``skip_links`` / ``keyboard_shortcuts`` / ``aria_labels`` 是纯生成
  - 端点注册与公开读 / 鉴权分流

真实配置持久化（``system_settings`` 的 ``accessibility.config``）走运行时验证。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.system.accessibility.service import (
    CONFIG_KEY,
    DEFAULT_CONFIG,
    FONT_SIZE_PX,
    accessibility_service,
)

BASE = "/api/v3/system/accessibility"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 校验（按元素）
def test_validate_flags_missing_alt_only_for_the_offending_image():
    """v2 的整篇子串判断在这里会漏报：一张有 alt、一张没有"""
    html = '<img src="a.png" alt="有描述"><img src="b.png">'

    result = accessibility_service.validate(html)

    assert result["valid"] is False
    rules = [item["rule"] for item in result["errors"]]
    assert "img-alt" in rules
    assert result["summary"]["errors"] == 1


def test_validate_accepts_decorative_alt():
    html = '<html lang="zh-CN"><body><img src="a.png" alt=""></body></html>'

    result = accessibility_service.validate(html)

    assert "img-alt" not in [item["rule"] for item in result["errors"]]


def test_validate_detects_duplicate_ids():
    result = accessibility_service.validate('<div id="x"></div><div id="x"></div>')

    assert "duplicate-id" in [item["rule"] for item in result["errors"]]


def test_validate_flags_button_without_accessible_name():
    result = accessibility_service.validate("<button></button>")

    assert "button-name" in [item["rule"] for item in result["errors"]]


def test_validate_accepts_button_with_aria_label():
    result = accessibility_service.validate('<button aria-label="关闭"></button>')

    assert "button-name" not in [item["rule"] for item in result["errors"]]


def test_validate_warns_on_vague_link_text():
    result = accessibility_service.validate('<a href="/x">点击这里</a>')

    assert "link-text-vague" in [item["rule"] for item in result["warnings"]]


def test_validate_warns_on_unlabelled_input_and_accepts_label_for():
    without = accessibility_service.validate('<input type="text" name="q">')
    with_label = accessibility_service.validate('<label for="q">搜索</label><input type="text" id="q">')

    assert "form-label" in [item["rule"] for item in without["warnings"]]
    assert "form-label" not in [item["rule"] for item in with_label["warnings"]]


def test_validate_heading_hierarchy():
    no_h1 = accessibility_service.validate("<h2>只有二级</h2>")
    skip = accessibility_service.validate("<h1>一级</h1><h4>四级</h4>")

    assert "heading-hierarchy" in [item["rule"] for item in no_h1["warnings"]]
    assert "heading-order" in [item["rule"] for item in skip["warnings"]]


def test_validate_warns_on_positive_tabindex_and_unknown_role():
    result = accessibility_service.validate('<div tabindex="3" role="notarole"></div>')
    rules = [item["rule"] for item in result["warnings"]]

    assert "positive-tabindex" in rules
    assert "aria-role-valid" in rules


def test_validate_warns_on_autoplay_media_and_iframe_without_title():
    result = accessibility_service.validate('<video autoplay></video><iframe src="/x"></iframe>')
    rules = [item["rule"] for item in result["warnings"]]

    assert "media-autoplay" in rules
    assert "iframe-title" in rules


def test_validate_score_and_summary_shape():
    result = accessibility_service.validate('<html lang="zh-CN"><h1>好</h1></html>')

    assert result["valid"] is True
    assert result["score"] == 100
    assert set(result["summary"]) == {"errors", "warnings", "infos", "elements_checked"}
    assert result["summary"]["elements_checked"] >= 2


def test_validate_rejects_empty_html():
    with pytest.raises(BadRequestError):
        accessibility_service.validate("   ")


# ------------------------------------------------------------------ 生成
def test_css_reflects_config():
    css = accessibility_service.css(
        {**DEFAULT_CONFIG, "high_contrast_mode": True, "font_size": "x-large", "reduce_motion": True}
    )

    assert "20px" in css
    assert ".high-contrast" in css
    assert "prefers-reduced-motion" in css


def test_css_with_minimal_config_has_no_high_contrast_block():
    css = accessibility_service.css(
        {**DEFAULT_CONFIG, "high_contrast_mode": False, "reduce_motion": False, "skip_links": False}
    )

    assert ".high-contrast" not in css
    assert "--a11y-font-size" in css


def test_aria_labels_known_and_unknown():
    assert accessibility_service.aria_labels("navigation")["role"] == "navigation"
    assert accessibility_service.aria_labels("search", {"label": "找文章"})["aria_label"] == "找文章"

    with pytest.raises(BadRequestError):
        accessibility_service.aria_labels("nope")


def test_skip_links_and_shortcuts_shape():
    links = accessibility_service.skip_links()
    shortcuts = accessibility_service.keyboard_shortcuts()

    assert all({"id", "text", "target", "aria_label"} <= set(item) for item in links)
    assert all({"keys", "action"} <= set(item) for item in shortcuts)


def test_guide_lists_every_config_key():
    guide = accessibility_service.guide()
    keys = {item["key"] for item in guide["features"]}

    assert keys == set(DEFAULT_CONFIG)
    assert set(FONT_SIZE_PX) == {"small", "medium", "large", "x-large"}


def test_config_key_constant():
    assert CONFIG_KEY == "accessibility.config"


# ------------------------------------------------------------------ 端点


def test_public_reads_and_protected_writes():
    client = TestClient(_app(), raise_server_exceptions=False)

    for path in ("config", "css", "skip-links", "shortcuts", "guide"):
        assert client.get(f"{BASE}/{path}").status_code not in (401, 403), path
    assert client.put(f"{BASE}/config", json={"high_contrast_mode": True}).status_code in (401, 403)
    assert client.post(f"{BASE}/validate", json={"html": "<p>x</p>"}).status_code in (401, 403)
    # 公开的 POST 不应被鉴权拦下
    assert client.post(f"{BASE}/aria", json={"element_type": "search"}).status_code not in (401, 403)
