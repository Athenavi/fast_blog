"""Markdown → HTML **片段**渲染（前台文章正文用）。

## 为什么单独一个模块，而不复用 `utils/filters.py` 的 `md2html`

`md2html()` 产出的是**完整文档**：它自带 `<style>…</style>` 与
`<div class="markdown-content">` 包裹，适合"独立渲染一段 Markdown"。而文章正文要嵌进
SSR 的文章页，只能要**片段** —— 否则页面里会多出一份重复的样式块和一层多余容器。

## 为什么需要它（对应两个真实缺陷）

前台投稿编辑器的【源码】模式允许写 Markdown（i18n 文案就是"支持 HTML / Markdown 源码"），
它与富文本模式**共用同一个 `form.content`**，但此前**没有任何渲染路径**：

  1. 详情页只做 `v-html`，于是 Markdown 标记（`#`、`**`、`- `、`1. `）原样显示；
  2. 作者在源码模式写的有序列表序号（`1.` `2.`）被当作**字面文本**存进正文 ——
     富文本模式下这些序号由 `<ol>` + CSS 生成，源码模式下不是。

## 为什么在服务端转，而不是前端加个 markdown 库

前台是 SSR，SEO 的胜负手是"爬虫拿到的 HTML"。Markdown 直出的损失是结构性的：
标题层级丢失、**内链不可爬**（最严重 —— 直接损失站内权重传递）、图片 alt 丢失、
关键词被 `*`/`#` 污染、以及详情页的目录抽取拿不到 `<h2>/<h3>` 而整个目录为空。

服务端转换让 SSR **直接吐出正确 HTML**，且**不引入任何客户端依赖**
（不加 bundle、不加首屏开销，保住 Core Web Vitals）。同时**保留作者写的源码** ——
若改成"保存时转 HTML"，源码模式下次打开会看到被 HTML 顶替的内容，编辑体验断裂。

## 安全

与 `filters.md2html` 同一取向：`html=False`，Markdown 里的原始 HTML 一律**转义**。
正文最终经 `v-html` 注入页面，不转义就等于开了存储型 XSS 的口子。
"""

from __future__ import annotations

import re
from typing import Any

from markdown_it import MarkdownIt
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

from src.utils.html_sanitizer import sanitize_html

#: 命中这些标签就认为内容已经是 HTML。
#:
#: 判据用"是否含 HTML 标签"而不是"是否含 Markdown 记号"，因为后者误判面更大：
#: 正文里出现一个 `*` 或行首 `#`（例如话题标签）就会把 HTML 内容误当 Markdown 再渲染一遍，
#: 那会把正常 HTML 转义成源码显示。而富文本编辑器（Tiptap）的输出**必然**含块级标签，
#: 所以正向判据既简单又可靠。
_HTML_TAG_RE = re.compile(
    r"</?(?:p|div|h[1-6]|ul|ol|li|pre|code|blockquote|table|thead|tbody|tr|td|th"
    r"|img|a|strong|em|span|figure|figcaption|section|article|hr|br|iframe|video|audio)\b",
    re.IGNORECASE,
)

#: 标题降级级数：Markdown 的 `#` 会生成 `<h1>`，而文章页的标题本身就是 `<h1>`。
#: 一页多个 `<h1>` 是结构语义上的反模式，所以整体降一级（`#` → `<h2>`）。
_HEADING_SHIFT = 1


def looks_like_html(content: str) -> bool:
    """内容是否已经是 HTML（而非 Markdown 源码）。"""
    return bool(_HTML_TAG_RE.search(content or ""))


def _shift_level(tag: str) -> str:
    """`h1` → `h2`，并在 `h6` 处饱和。"""
    return f"h{min(int(tag[1:]) + _HEADING_SHIFT, 6)}"


def _demote_headings(state: Any) -> None:
    """把正文标题整体降一级（`#` → `<h2>`）。

    在 **core 阶段改 token**，而不是覆盖 renderer rule：markdown-it-py 的 renderer
    rule 签名是 `(tokens, idx, options, env)`，**没有** JS 版的 `self` 参数 ——
    照 JS 写法加 `self` 会直接 `TypeError`。改 token 与渲染实现解耦，也不会因为
    上游 renderer 内部变化而失效。
    """
    for token in state.tokens:
        if token.type in ("heading_open", "heading_close"):
            token.tag = _shift_level(token.tag)


def _build_renderer() -> MarkdownIt:
    """构造渲染器。

    只启用正文真正需要的能力，并且**不做**代码高亮：前端详情页已有
    `lib/highlight.ts`（highlight.js，按需动态加载）会对 `<pre><code>` 着色，
    服务端再算一遍纯属重复劳动，还会把 Pygments 的内联样式带进 SSR 输出。
    """
    md = MarkdownIt(
        "commonmark",
        {
            # 允许原始 HTML 通过 —— 作者会用 `<table>` / `<img width>` 排版。
            # **安全性不靠这里**：渲染结果会整体过一遍白名单净化
            # （见 render_markdown_fragment），那一步才是 XSS 的防线。
            "html": True,
            # 不把单个换行当 <br>：Markdown 的段落语义就是这样，也避免正文被切碎
            "breaks": False,
            "linkify": False,
            "typographer": False,
        },
    )
    md.enable("table")
    # GFM 删除线 `~~…~~`：commonmark 预设不含，必须显式启用
    md.enable("strikethrough")
    md.use(tasklists_plugin, enabled=True, label=True)
    # 脚注 `[^x]` 与定义型列表（`名词` 换行 `: 定义`）：作者文档里的常见写法
    md.use(footnote_plugin)
    md.use(deflist_plugin)
    md.core.ruler.push("demote_headings", _demote_headings)
    return md


_renderer: MarkdownIt | None = None


def _get_renderer() -> MarkdownIt:
    """惰性构造并复用（`MarkdownIt` 的构建比渲染贵，没必要每次请求都建）。"""
    global _renderer
    if _renderer is None:
        _renderer = _build_renderer()
    return _renderer


def render_markdown_fragment(text: str) -> str:
    """Markdown → HTML 片段（不含 `<style>` 与容器包裹）。

    渲染结果会过一遍 `html_sanitizer`：Markdown 里可以写任意 HTML，
    而正文最终经 `v-html` 注入页面，**净化这一步是 XSS 的唯一防线**。
    """
    if not text:
        return ""
    return sanitize_html(_get_renderer().render(text))


def render_content_for_display(content: str | None) -> str | None:
    """把正文规整成"可直接放进页面的 HTML"。

    - 已是 HTML（富文本编辑器产出）→ 净化后返回；
    - 看起来是 Markdown → 转成 HTML 片段（同样净化）；
    - 空值 → 原样返回（`None`/`""`），让调用方走自己的空态分支。

    **HTML 分支也要净化**：后端写入正文时并没有做任何清洗（`content/article/` 里
    搜不到 `sanitize`/`escape_html`），而正文还能经 API 直接写入 —— 不能因为
    "它是富文本产出的"就假定它安全。
    """
    if not content:
        return content
    if looks_like_html(content):
        return sanitize_html(content)
    return render_markdown_fragment(content)
