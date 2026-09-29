"""_pending_test_amp.py —— 待迁入 ``tests/`` 的 AMP 模块**纯函数**单测

本任务执行环境**禁止写 ``tests/`` 目录、禁止执行 shell**，因此把 ``content/amp``
模块的纯函数单测临时放在模块目录内。文件名以 ``_`` 开头，不会被当作业务模块导入
（模块 ``__init__.py`` 只导出 :data:`amp_service`）。**恢复后应移动到**
``tests/test_v3_amp.py``。

只覆盖**不依赖 DB / 网络 / FastAPI 请求上下文**的纯函数与常量::

  - ``convert_html_fragment`` 元素级转换：``img→amp-img`` / ``video→amp-video`` /
    ``audio→amp-audio``、禁用标签整棵子树剥离、内联事件属性（``on*``）剥离、
    ``<style>`` 收集、文本转义、自闭合 / 媒体默认属性补全
  - ``limit_css`` 按**字节**截断（含「恰好等于上限」「标记占满预算」「多字节被切断」边界）
  - ``to_datetime`` datetime / ISO 字符串归一与回退（int 见文末说明）
  - ``AmpService.validate_amp`` 逐项违规 + 合规用例
  - ``AmpService.render_document`` / ``convert_to_amp`` / ``build_document`` 文档骨架
  - 常量表健全性（``TAG_MAP`` / ``DISALLOWED_TAGS`` / ``FORBIDDEN_TAGS`` /
    ``COMPONENT_SCRIPTS`` / ``CSS_LIMIT_BYTES`` / ``ALLOWED_SCRIPT_HOST`` 等）

上述每个断言都逐行对照 ``service.py`` 真实实现写成（不改 src、不做占位断言）。

运行（在仓库根目录，确保可 ``import src.*``）::

    python -m pytest src/api/v3/modules/content/amp/_pending_test_amp.py -q

**本文件尚未运行**：本任务执行环境不允许跑 shell / pytest，故仅静态编写。
"""

from datetime import datetime

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.content.amp.service import (
    ALLOWED_SCRIPT_HOST,
    AMP_BOILERPLATE,
    AMP_RUNTIME,
    BASE_CSS,
    COMPONENT_SCRIPTS,
    CSS_LIMIT_BYTES,
    DEFAULT_SITE_NAME,
    DISALLOWED_TAGS,
    FORBIDDEN_TAGS,
    TAG_MAP,
    VOID_TAGS,
    AmpService,
    amp_service,
    convert_html_fragment,
    limit_css,
    to_datetime,
)


def _rules(result, key="errors"):
    """从校验结果里取出某一类（errors / warnings）的规则名列表"""
    return [item["rule"] for item in result[key]]


# ===================================================================== 常量表
def test_constants_look_sane():
    assert CSS_LIMIT_BYTES == 75 * 1024
    assert ALLOWED_SCRIPT_HOST == "cdn.ampproject.org"
    assert DEFAULT_SITE_NAME == "FastBlog"
    assert TAG_MAP == {"img": "amp-img", "video": "amp-video", "audio": "amp-audio"}
    assert set(COMPONENT_SCRIPTS) == {"amp-img", "amp-video", "amp-audio"}
    for name, script in COMPONENT_SCRIPTS.items():
        assert f'custom-element="{name}"' in script
        assert ALLOWED_SCRIPT_HOST in script
    # 要替换的媒体标签不能同时又属于「移除」集合
    assert DISALLOWED_TAGS.isdisjoint(TAG_MAP)
    # 校验阶段禁用集合是转换阶段移除集合的子集；script 单独按 src/type 判定
    assert FORBIDDEN_TAGS <= DISALLOWED_TAGS
    assert "script" not in FORBIDDEN_TAGS
    # 空元素集合与媒体标签不重叠
    assert {"img"} <= VOID_TAGS
    assert "video" not in VOID_TAGS and "audio" not in VOID_TAGS


def test_runtime_and_boilerplate_constants():
    assert "cdn.ampproject.org/v0.js" in AMP_RUNTIME
    assert "amp-boilerplate" in AMP_BOILERPLATE
    assert "body{font-family" in BASE_CSS


# ==================================================== convert_html_fragment
def test_convert_img_to_amp_img_with_defaults():
    # <img> 是空元素：映射为 amp-img，输出自闭合，并补全默认宽高 / layout / alt
    result = convert_html_fragment('<img src="a.png">')
    assert result["html"] == (
        '<amp-img src="a.png" width="800" height="600" '
        'layout="responsive" alt=""></amp-img>'
    )
    assert result["css"] == ""
    assert result["removed_tags"] == []


def test_convert_video_to_amp_video():
    result = convert_html_fragment('<video src="v.mp4" controls></video>')
    html = result["html"]
    assert html.startswith("<amp-video ")
    assert "</amp-video>" in html
    assert 'src="v.mp4"' in html
    # 布尔属性（无值）原样保留为裸属性名
    assert " controls" in html
    # video 默认 640x360、responsive
    assert 'width="640"' in html and 'height="360"' in html
    assert 'layout="responsive"' in html


def test_convert_audio_to_amp_audio():
    result = convert_html_fragment('<audio src="a.mp3"></audio>')
    html = result["html"]
    assert html.startswith("<amp-audio ")
    assert "</amp-audio>" in html
    # audio 默认 640x50、fixed
    assert 'width="640"' in html and 'height="50"' in html
    assert 'layout="fixed"' in html


def test_disallowed_subtree_removed():
    result = convert_html_fragment("<div>a<script>bad()</script>b</div>")
    assert result["html"] == "<div>ab</div>"
    assert result["removed_tags"] == ["script"]


def test_disallowed_nested_subtree_removed():
    # <form> 整棵子树（含内部 input/p）都被丢弃；只有最外层被记进 removed
    result = convert_html_fragment("<form><input><p>x</p></form>tail")
    assert result["html"] == "tail"
    assert result["removed_tags"] == ["form"]


def test_void_disallowed_tags_removed():
    # base / link 既是禁用标签又是空元素：只记录、不开启跳过栈
    result = convert_html_fragment("<p>x</p><base href='/'><link rel='x'>")
    assert result["html"] == "<p>x</p>"
    assert result["removed_tags"] == ["base", "link"]


def test_removed_tags_are_deduped():
    result = convert_html_fragment("<script>1</script><script>2</script>")
    assert result["removed_tags"] == ["script"]


def test_inline_event_attrs_stripped():
    result = convert_html_fragment('<p onclick="evil()" class="x">t</p>')
    assert result["html"] == '<p class="x">t</p>'
    assert "onclick" not in result["html"]


def test_inline_event_attrs_case_insensitive():
    # 属性名统一转小写后再判 on 前缀
    result = convert_html_fragment('<p OnClick="evil()" CLASS="x">t</p>')
    assert result["html"] == '<p class="x">t</p>'


def test_style_collected_into_css():
    result = convert_html_fragment("<style>.a{color:red}</style><p>x</p>")
    assert result["css"] == ".a{color:red}"
    assert result["html"] == "<p>x</p>"


def test_multiple_style_blocks_concatenated():
    result = convert_html_fragment("<style>.a{}</style><style>.b{}</style>")
    assert result["css"] == ".a{}.b{}"
    assert result["html"] == ""


def test_text_is_escaped():
    # 实体先被解析回 &，再在输出时按 quote=False 重新转义（不转义引号）
    result = convert_html_fragment("<p>Tom &amp; Jerry</p>")
    assert result["html"] == "<p>Tom &amp; Jerry</p>"


def test_empty_inputs():
    assert convert_html_fragment("") == {"html": "", "css": "", "removed_tags": []}
    assert convert_html_fragment("   ") == {"html": "", "css": "", "removed_tags": []}
    assert convert_html_fragment(None) == {"html": "", "css": "", "removed_tags": []}


# ================================================================== limit_css
def test_limit_css_within_limit_returns_unchanged():
    css = "a" * 100
    assert limit_css(css, 100) == (css, False)


def test_limit_css_exact_boundary_not_truncated():
    # 字节数恰好等于 limit → 不截断
    assert limit_css("abcd", 4) == ("abcd", False)


def test_limit_css_output_bytes_equal_limit():
    # 超限时先扣掉截断标记占用的字节再截断；输入全 ASCII 时输出字节数恰好等于 limit
    out, truncated = limit_css("a" * 300, 200)
    assert truncated is True
    assert len(out.encode("utf-8")) == 200
    assert out.startswith("a")
    assert "已截断" in out


def test_limit_css_multibyte_not_split():
    # 按字节截断时不能把多字节字符切成半个（decode errors="ignore" 丢弃残字节）
    out, truncated = limit_css("中" * 100, 100)  # 300 字节
    assert truncated is True
    assert "\ufffd" not in out
    assert out.startswith("中")
    assert "已截断" in out


def test_limit_css_marker_when_budget_zero():
    # limit 小于截断标记长度 → 预算被夹到 0，只剩标记本身
    out, truncated = limit_css("abcde", 4)
    assert truncated is True
    assert out.startswith("\n/*")
    assert "已截断" in out
    assert out.endswith("*/\n")


# ================================================================= to_datetime
def test_to_datetime_none_and_passthrough():
    assert to_datetime(None) is None
    dt = datetime(2024, 5, 6, 7, 8, 9)
    assert to_datetime(dt) is dt


def test_to_datetime_iso_strings():
    assert to_datetime("2024-01-02T03:04:05") == datetime(2024, 1, 2, 3, 4, 5)
    # 结尾的 Z（UTC 标记）被 replace 掉后再解析
    assert to_datetime("2024-01-02T03:04:05Z") == datetime(2024, 1, 2, 3, 4, 5)
    assert to_datetime("2024-01-02") == datetime(2024, 1, 2, 0, 0, 0)
    parsed = to_datetime("2024-01-02T03:04:05.123456")
    assert parsed.microsecond == 123456


def test_to_datetime_invalid_returns_none():
    assert to_datetime("not-a-date") is None
    assert to_datetime("") is None


# ============================================ validate_amp（合规 / 逐项违规）
VALID_DOC = (
    "<!doctype html>\n"
    '<html amp lang="zh-CN">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width">\n'
    '<link rel="canonical" href="https://example.com/a">\n'
    "<title>T</title>\n"
    "<style amp-boilerplate>body{}</style>\n"
    '<script async src="https://cdn.ampproject.org/v0.js"></script>\n'
    "<style amp-custom>body{color:red}</style>\n"
    "</head>\n"
    "<body><p>hello</p></body>\n"
    "</html>"
)


def test_validate_valid_document():
    result = amp_service.validate_amp(VALID_DOC)
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["summary"]["css_limit"] == CSS_LIMIT_BYTES
    assert result["summary"]["errors"] == 0
    assert result["summary"]["elements_checked"] > 0


def test_validate_valid_flag_matches_errors():
    ok = amp_service.validate_amp(VALID_DOC)
    bad = amp_service.validate_amp("<p>x</p>")
    assert ok["valid"] is (len(ok["errors"]) == 0)
    assert bad["valid"] is (len(bad["errors"]) == 0)


def test_validate_requires_amp_attribute():
    html = VALID_DOC.replace('<html amp lang="zh-CN">', '<html lang="zh-CN">')
    result = amp_service.validate_amp(html)
    assert result["valid"] is False
    assert "missing-amp-attribute" in _rules(result)


def test_validate_accepts_lightning_attr():
    # ⚡ 是 amp 的等价写法，不应报 missing-amp-attribute
    html = VALID_DOC.replace('<html amp lang="zh-CN">', '<html \u26a1 lang="zh-CN">')
    result = amp_service.validate_amp(html)
    assert "missing-amp-attribute" not in _rules(result)


def test_validate_missing_all_required_head_tags():
    result = amp_service.validate_amp("<p>x</p>")
    rules = _rules(result)
    assert "missing-amp-attribute" in rules
    assert "missing-charset" in rules
    assert "missing-viewport" in rules
    assert "missing-canonical" in rules
    assert result["valid"] is False


def test_validate_missing_canonical_only():
    html = VALID_DOC.replace('<link rel="canonical" href="https://example.com/a">\n', "")
    result = amp_service.validate_amp(html)
    assert "missing-canonical" in _rules(result)
    assert "missing-charset" not in _rules(result)


def test_validate_inline_event_handler():
    html = VALID_DOC.replace("<body>", '<body onload="init()">')
    result = amp_service.validate_amp(html)
    assert "inline-event-handler" in _rules(result)


def test_validate_forbidden_tag():
    html = VALID_DOC.replace("<body><p>hello</p></body>", "<body><iframe></iframe></body>")
    result = amp_service.validate_amp(html)
    assert "forbidden-tag" in _rules(result)


def test_validate_forbidden_script_and_allowed_scripts():
    bad = VALID_DOC.replace(
        '<script async src="https://cdn.ampproject.org/v0.js"></script>\n',
        '<script src="https://evil.example/x.js"></script>\n',
    )
    assert "forbidden-script" in _rules(amp_service.validate_amp(bad))

    # ld+json 的结构化数据脚本合法，不报 forbidden-script
    good = VALID_DOC.replace(
        "</head>",
        '<script type="application/ld+json">{}</script>\n</head>',
    )
    assert "forbidden-script" not in _rules(amp_service.validate_amp(good))


def test_validate_img_warns_but_still_valid():
    html = VALID_DOC.replace("<body><p>hello</p></body>", '<body><img src="a.png"></body>')
    result = amp_service.validate_amp(html)
    assert "use-amp-img" in _rules(result, "warnings")
    assert result["valid"] is True


def test_validate_missing_boilerplate_is_warning_only():
    html = VALID_DOC.replace("<style amp-boilerplate>body{}</style>\n", "")
    result = amp_service.validate_amp(html)
    assert "missing-boilerplate" in _rules(result, "warnings")
    assert "missing-boilerplate" not in _rules(result)
    assert result["valid"] is True


def test_validate_css_limit():
    big_css = "x" * (CSS_LIMIT_BYTES + 10)
    html = VALID_DOC.replace("body{color:red}", big_css)
    result = amp_service.validate_amp(html)
    assert "css-limit" in _rules(result)
    assert result["summary"]["css_bytes"] > CSS_LIMIT_BYTES


def test_validate_empty_raises():
    with pytest.raises(BadRequestError):
        amp_service.validate_amp("")
    with pytest.raises(BadRequestError):
        amp_service.validate_amp("   ")


# ======================== render_document / convert_to_amp / build_document
def test_render_document_skeleton():
    rendered = AmpService().render_document(
        title="标题",
        content_html="<p>正文</p>",
        author_name="张三",
        published_at="2024-01-02T03:04:05",
        canonical_url="https://example.com/post/1",
        language="zh-CN",
    )
    html = rendered["html"]
    assert html.startswith("<!doctype html>")
    assert '<html amp lang="zh-CN">' in html
    assert '<meta charset="utf-8">' in html
    assert 'name="viewport"' in html
    assert 'rel="canonical"' in html
    assert 'href="https://example.com/post/1"' in html
    assert "<title>标题</title>" in html
    assert "amp-boilerplate" in html
    assert "cdn.ampproject.org/v0.js" in html
    assert "<style amp-custom>" in html
    assert '<div class="amp-content">' in html


def test_render_document_structured_data_and_meta():
    rendered = AmpService().render_document(
        title="标题",
        content_html="<p>x</p>",
        author_name="张三",
        published_at="2024-01-02T03:04:05",
    )
    html = rendered["html"]
    assert '"@type": "NewsArticle"' in html
    assert '"headline": "标题"' in html
    assert '"datePublished": "2024-01-02T03:04:05"' in html
    assert "作者：张三" in html
    assert "发布时间：2024-01-02" in html


def test_render_document_components_detected_from_body():
    rendered = AmpService().render_document(
        content_html='<img src="a.png"><video src="v.mp4"></video>',
    )
    # components 顺序固定为 amp-img / amp-video / amp-audio
    assert rendered["components"] == ["amp-img", "amp-video"]
    html = rendered["html"]
    assert 'custom-element="amp-img"' in html
    assert 'custom-element="amp-video"' in html
    assert 'custom-element="amp-audio"' not in html


def test_render_document_removed_tags_and_css_metrics():
    rendered = AmpService().render_document(
        content_html="<p>x</p><iframe src='x'></iframe>",
        extra_css=".extra{color:blue}",
    )
    assert rendered["removed_tags"] == ["iframe"]
    assert rendered["css_limit"] == CSS_LIMIT_BYTES
    assert rendered["css_truncated"] is False
    # css_bytes 与返回的 css 的 UTF-8 长度一致
    assert rendered["css_bytes"] == len(rendered["css"].encode("utf-8"))
    assert "body{font-family" in rendered["css"]
    assert ".extra{color:blue}" in rendered["css"]


def test_render_document_featured_image_uses_amp_img():
    rendered = AmpService().render_document(
        title="标题",
        content_html="<p>x</p>",
        featured_image="https://example.com/cover.jpg",
    )
    html = rendered["html"]
    assert 'https://example.com/cover.jpg' in html
    assert 'width="800" height="450"' in html


def test_render_document_components_include_featured_image():
    # 封面图的 <amp-img> 也在文档里出现，HEAD 必须注入 amp-img 组件脚本，
    # 否则生成的文档带 amp-img 元素却没有对应脚本，真实 AMP 校验会失败。
    rendered = AmpService().render_document(
        title="t",
        content_html="<p>x</p>",
        featured_image="https://example.com/cover.jpg",
    )
    assert rendered["components"] == ["amp-img"]
    assert "<amp-img" in rendered["html"]
    assert 'custom-element="amp-img"' in rendered["html"]


def test_render_document_components_keep_canonical_order():
    # 正文含 video + 封面图时仍按固定顺序（amp-img, amp-video, amp-audio）
    rendered = AmpService().render_document(
        title="t",
        content_html="<video src='a.mp4'></video>",
        featured_image="https://example.com/cover.jpg",
    )
    assert rendered["components"] == ["amp-img", "amp-video"]


def test_render_document_return_keys():
    rendered = AmpService().render_document(content_html="<p>x</p>", canonical_url="https://e/a")
    assert set(rendered) == {
        "html",
        "css",
        "css_bytes",
        "css_limit",
        "css_truncated",
        "components",
        "removed_tags",
        "canonical_url",
    }
    assert rendered["canonical_url"] == "https://e/a"


def test_build_document_returns_html_only():
    html = AmpService().build_document(title="t", content_html="<p>x</p>")
    assert isinstance(html, str)
    assert html.startswith("<!doctype html>")
    assert "<html amp" in html


def test_convert_to_amp_returns_validation_and_metrics():
    result = AmpService().convert_to_amp(html="<p>hi</p><img src='a.png'>")
    assert set(result) == {
        "amp_html",
        "canonical_url",
        "components",
        "removed_tags",
        "css",
        "validation",
    }
    assert "<html amp" in result["amp_html"]
    assert result["components"] == ["amp-img"]
    assert result["removed_tags"] == []
    assert set(result["css"]) == {"bytes", "limit", "truncated"}
    assert result["css"]["limit"] == CSS_LIMIT_BYTES
    # 生成的文档自身应通过 AMP 校验
    assert result["validation"]["valid"] is True


def test_convert_to_amp_empty_raises():
    with pytest.raises(BadRequestError):
        AmpService().convert_to_amp(html="   ")
