# -*- coding: utf-8 -*-
"""正文渲染：Markdown → HTML 片段（`src/utils/markdown.py`）+ 白名单净化（`html_sanitizer.py`）。

覆盖四类断言：

1. **格式判定**：富文本产出的 HTML 与 Markdown 源码分别走哪条路径；
2. **用户报的渲染缺陷**：GFM 删除线、原始 HTML（`<table>` / `<img>`）、脚注、定义型列表
   —— 这些此前都渲染不出来（HTML 更是被整段转义成源码）；
3. **SEO 结构**：标题降级（`#` → `<h2>`，避免与文章标题的 `<h1>` 形成"一页多 h1"）、
   内链解析成可爬的 `<a>`、图片 alt 保留；
4. **安全**：正文最终经 `v-html` 注入页面，而**后端写入时没有任何清洗**，
   所以这里是 XSS 的唯一防线 —— `script`/`on*`/`javascript:`/`style` 必须被剔除，
   含 `DOCTYPE`/`ENTITY` 的输入直接拒绝。
"""

import pytest

from src.utils.html_sanitizer import UnsafeHtmlError, sanitize_html
from src.utils.markdown import (
    looks_like_html,
    render_content_for_display,
    render_markdown_fragment,
)


class TestFormatDetection:
    def test_rich_text_html_is_passed_through(self):
        """富文本编辑器（Tiptap）的产物必须原样语义返回（只过净化，不改结构）。"""
        html = '<p>段落</p><h2>标题</h2><ul><li>项</li></ul>'
        assert render_content_for_display(html) == html

    def test_markdown_is_converted(self):
        out = render_content_for_display('# 标题\n\n正文 **粗体**')
        assert '<h2' in out and '标题' in out
        assert '<strong>粗体</strong>' in out

    def test_empty_is_passed_through(self):
        assert render_content_for_display('') == ''
        assert render_content_for_display(None) is None

    def test_looks_like_html(self):
        assert looks_like_html('<p>x</p>')
        assert not looks_like_html('# 标题\n\n正文')

    def test_plain_text_with_symbols_is_not_html(self):
        """含 `*` 的纯文本不能被当成 HTML。"""
        assert not looks_like_html('价格 * 数量 = 总价')


class TestReportedDefects:
    """用户拿真实文档报出来的、此前渲染不出来的内容。"""

    def test_gfm_strikethrough(self):
        out = render_markdown_fragment('~~这是一段错误的文本。~~')
        assert '<s>' in out
        assert '~~' not in out

    def test_raw_html_table_is_kept(self):
        """作者用 HTML 写表格是常见需求；此前整段被转义成源码。"""
        src = '<table>\n<tr><th>值班人员</th><th>星期一</th></tr>\n<tr><td>李强</td><td>张明</td></tr>\n</table>'
        out = render_markdown_fragment(src)
        assert '<table>' in out
        assert '<th>值班人员</th>' in out
        assert '&lt;table&gt;' not in out

    def test_raw_html_img_with_size_is_kept(self):
        out = render_markdown_fragment(
            '<img src="http://leanote.com/images/logo/leanote_icon_blue.png" width="50px" />'
        )
        assert '<img' in out
        assert 'width="50px"' in out
        assert '&lt;img' not in out

    def test_footnote(self):
        out = render_markdown_fragment(
            'Leanote[^footnote]来创建一个脚注\n\n[^footnote]: Leanote是一款开源云笔记产品.'
        )
        assert 'footnote' in out.lower()
        assert '[^footnote]' not in out

    def test_definition_list(self):
        out = render_markdown_fragment('名词 1\n:   定义 1')
        assert '<dl>' in out
        assert '<dt>' in out
        assert '<dd>' in out

    def test_ordered_list_numbers_are_not_literal_text(self):
        """源码模式写的 `1.` `2.` 必须变成真正的 `<ol>`（回归）。"""
        out = render_markdown_fragment('1. 第一点\n2. 第二点')
        assert '<ol>' in out
        assert '<li>第一点</li>' in out
        assert '1. 第一点' not in out

    def test_source_mode_document_renders(self):
        """整篇 Leanote 风格的文档：各类语法都应产出对应标签。"""
        source = (
            '# Welcome\n\n## 1. 排版\n\n**粗体** *斜体*\n\n~~错误文本~~\n\n'
            '> 引用\n\n1. 支持Vim\n2. 支持Emacs\n\n - 项目1\n - 项目2\n\n'
            '## 5.1 表格\n\nItem | Value\n---- | ---\nComputer | 1600\n\n'
            '``` javascript\nvar a = 1;\n```\n'
        )
        out = render_content_for_display(source)
        for expected in ('<h2', '<h3', '<strong>', '<em>', '<s>', '<blockquote>',
                         '<ol>', '<ul>', '<table>', '<pre>'):
            assert expected in out, f'缺少 {expected}'


class TestSeoStructure:
    def test_heading_is_demoted_to_avoid_duplicate_h1(self):
        out = render_markdown_fragment('# 一级\n\n## 二级\n\n### 三级')
        assert '<h2' in out and '一级' in out
        assert '<h3' in out and '二级' in out
        assert '<h4' in out and '三级' in out
        assert '<h1' not in out

    def test_headings_saturate_at_h6(self):
        assert '<h6' in render_markdown_fragment('###### 六级')

    def test_internal_link_becomes_crawlable_anchor(self):
        out = render_markdown_fragment('见 [另一篇](/articles/other)')
        assert '<a href="/articles/other"' in out
        assert '另一篇' in out

    def test_image_alt_is_preserved(self):
        out = render_markdown_fragment('![配图说明](/x.png)')
        assert 'alt="配图说明"' in out

    def test_table_is_rendered(self):
        out = render_markdown_fragment('| a | b |\n| - | - |\n| 1 | 2 |')
        assert '<table>' in out
        assert '<td>1</td>' in out

    def test_task_list_is_rendered(self):
        out = render_markdown_fragment('- [x] 已完成\n- [ ] 未完成')
        assert 'type="checkbox"' in out


class TestSafety:
    """正文最终经 `v-html` 注入，且后端写入时无清洗 —— 这里是唯一防线。"""

    def test_script_is_dropped_with_its_content(self):
        out = render_markdown_fragment('正常文本\n\n<script>alert(1)</script>')
        assert '<script' not in out
        assert 'alert(1)' not in out  # 整棵子树一起丢，不是只丢标签
        assert '正常文本' in out

    def test_event_handler_attributes_are_dropped(self):
        out = sanitize_html('<img src="/x.png" onerror="alert(1)" onclick="x()">')
        assert 'onerror' not in out
        assert 'onclick' not in out
        assert 'src="/x.png"' in out

    def test_javascript_url_is_dropped(self):
        for bad in ('javascript:alert(1)', 'JaVaScRiPt:alert(1)', 'java\tscript:alert(1)'):
            out = sanitize_html(f'<a href="{bad}">x</a>')
            assert 'href' not in out, f'{bad!r} 不该被放行'

    def test_data_url_is_dropped(self):
        out = sanitize_html('<img src="data:text/html;base64,PHNjcmlwdD4=">')
        assert 'src' not in out

    def test_style_attribute_is_dropped(self):
        out = sanitize_html('<div style="position:fixed;top:0">x</div>')
        assert 'style=' not in out

    def test_unknown_tags_are_dropped(self):
        out = sanitize_html('<iframe src="/x"></iframe><object></object><form></form>')
        assert '<iframe' not in out
        assert '<object' not in out
        assert '<form' not in out

    def test_doctype_is_rejected(self):
        with pytest.raises(UnsafeHtmlError):
            sanitize_html('<!DOCTYPE html><p>x</p>')
        with pytest.raises(UnsafeHtmlError):
            sanitize_html('<!ENTITY xxe SYSTEM "file:///etc/passwd">')

    def test_safe_urls_are_kept(self):
        for good in ('https://a.example.com/x', '/local/path', '#anchor', 'mailto:a@b.com'):
            out = sanitize_html(f'<a href="{good}">x</a>')
            assert f'href="{good}"' in out, f'{good!r} 应被放行'


class TestRichTextSemanticsPreserved:
    """净化不能把富文本编辑器依赖的语义弄丢。"""

    def test_code_language_class_is_kept(self):
        """代码块语言在 `class="language-x"` —— 前端据此做语法高亮。"""
        out = sanitize_html('<pre><code class="language-javascript">var a = 1;</code></pre>')
        assert 'class="language-javascript"' in out

    def test_callout_data_attribute_is_kept(self):
        out = sanitize_html('<div data-callout="warning"><p>注意</p></div>')
        assert 'data-callout="warning"' in out

    def test_table_colspan_rowspan_are_kept(self):
        out = sanitize_html('<table><tr><th rowspan="2">值班人员</th></tr></table>')
        assert 'rowspan="2"' in out
