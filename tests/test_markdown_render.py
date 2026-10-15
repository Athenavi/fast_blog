# -*- coding: utf-8 -*-
"""Markdown 正文渲染（`src/utils/markdown.py`）。

对应两个真实缺陷：

  1. 投稿编辑器的【源码】模式允许写 Markdown，但此前没有任何渲染路径 ——
     详情页只做 `v-html`，Markdown 标记原样显示；
  2. 源码模式里写的有序列表序号（`1.` `2.`）被当**字面文本**存进正文
     （富文本模式下这些序号由 `<ol>` + CSS 生成，源码模式下不是）。

本测试同时锁住 SEO 相关的结构：**标题降级**（`#` → `<h2>`，避免与文章标题的
`<h1>` 形成"一页多 h1"）、**内链解析成可爬的 `<a>`**（Markdown 直出时爬虫拿不到站内链接，
这是 SEO 损失最大的一条）、图片 alt 保留、表格/任务列表可用，
以及 `html=False` 的**转义**（正文最终经 `v-html` 注入，原始 HTML 不能原样输出）。
"""

from src.utils.markdown import (
    looks_like_html,
    render_content_for_display,
    render_markdown_fragment,
)


class TestFormatDetection:
    def test_rich_text_html_is_passed_through(self):
        """富文本编辑器（Tiptap）的产物必须原样返回，不能再渲染一遍。"""
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
        """含 `*` 的纯文本不能被当成 HTML —— 否则会被 `v-html` 原样注入。"""
        assert not looks_like_html('价格 * 数量 = 总价')


class TestSeoStructure:
    def test_heading_is_demoted_to_avoid_duplicate_h1(self):
        """`#` 必须变成 `<h2>`：文章页标题已是 `<h1>`，一页多 h1 是结构语义的反模式。"""
        out = render_markdown_fragment('# 一级\n\n## 二级\n\n### 三级')
        assert '<h2' in out and '一级' in out
        assert '<h3' in out and '二级' in out
        assert '<h4' in out and '三级' in out
        assert '<h1' not in out

    def test_headings_saturate_at_h6(self):
        assert '<h6' in render_markdown_fragment('###### 六级')

    def test_internal_link_becomes_crawlable_anchor(self):
        """内链必须解析成 `<a href>`：Markdown 直出时爬虫拿不到站内链接。"""
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
    def test_raw_html_in_markdown_is_escaped(self):
        """`html=False`：Markdown 里的原始 HTML 必须转义（正文最终经 `v-html` 注入）。"""
        out = render_markdown_fragment('正常文本\n\n<script>alert(1)</script>')
        assert '<script>' not in out
        assert '&lt;script&gt;' in out


class TestReportedDefect:
    """用户报告的现象：源码模式写的 Markdown 序号进了正文、且详情页不渲染。"""

    def test_ordered_list_numbers_are_not_literal_text(self):
        """`1.` `2.` 必须变成真正的 `<ol>`，而不是留在正文里的字面序号（bug 1）。"""
        out = render_markdown_fragment('1. 第一点\n2. 第二点')
        assert '<ol>' in out
        assert '<li>第一点</li>' in out
        assert '1. 第一点' not in out

    def test_source_mode_markdown_is_rendered_for_display(self):
        """源码模式写的整篇 Markdown 经出口后应是 HTML（bug 2）。"""
        source = '# 标题\n\n正文段落。\n\n1. 第一点\n2. 第二点\n\n> 引用'
        out = render_content_for_display(source)
        assert '<h2' in out
        assert '<p>正文段落。</p>' in out
        assert '<ol>' in out
        assert '<blockquote>' in out
        assert '#' not in out.split('>')[0]  # 开头的 `#` 不该作为文本留下
