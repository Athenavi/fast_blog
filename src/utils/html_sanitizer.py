"""HTML 白名单净化（正文渲染用）。

## 为什么需要

正文最终经 `v-html` 注入页面，而正文的两个来源**都会带 HTML**：

  - 富文本编辑器（Tiptap）本来就产出 HTML；
  - 【源码】模式允许作者直接写 HTML —— i18n 文案就写着"支持 HTML / Markdown 源码"。

此前 `utils/markdown.py` 用 `html=False` 把 Markdown 里的原始 HTML **一律转义**：
安全，但代价是作者写的 `<table>`、`<img>` 会变成源码显示，而且与富文本模式
**行为不一致**（同样的 HTML，富文本里能渲染、源码模式里不能）。

## 做法（沿用 `utils/upload/svg_sanitizer.py` 的既有范式）

**解析 + 白名单重建**，而不是黑名单过滤。黑名单（枚举 `<script>` / `on*` /
`javascript:`）可被"未列出的元素、实体编码、命名空间前缀"绕过，SVG 那边已经踩过这个坑。

具体规则：
  - 未知标签**整棵子树丢弃**（不是只丢标签本身，否则 `<script>` 的文本会漏出来）；
  - 属性按**每标签白名单**过滤；`on*` 一律丢弃（不依赖枚举）；
  - `href` / `src` 只允许安全协议与相对路径（`javascript:`、`data:`、`vbscript:` 等拒绝）；
  - `style` 属性**整体丢弃** —— 省去解析 CSS 的坑（`expression()`、`url()` 等）；
  - 含 `DOCTYPE` / `ENTITY` 的输入**直接拒绝**（防实体扩展攻击）；
  - 注释与处理指令丢弃。

用 `lxml.html` 而不是标准库 `ElementTree`：正文是 HTML 片段，`<br>`、`<img>` 这类
非自闭合写法在 XML 解析下会直接失败。
"""

from __future__ import annotations

import re

from lxml import etree
from lxml import html as lxml_html

#: 允许保留的标签（其余整棵子树丢弃）。覆盖正文常见排版需求。
ALLOWED_TAGS = frozenset({
    # 块级
    "p", "div", "section", "article", "blockquote", "pre", "hr", "br",
    "h1", "h2", "h3", "h4", "h5", "h6",
    # 列表
    "ul", "ol", "li", "dl", "dt", "dd",
    # 表格（用户文档里用 HTML 写表格是常见需求）
    "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup", "col",
    # 行内
    "a", "span", "strong", "b", "em", "i", "u", "s", "del", "ins", "mark", "small",
    # 任务列表的勾选框（Tiptap 的 TaskItem 产出；`input` 自身不能执行代码）
    "input",
    "sub", "sup", "code", "kbd", "samp", "var", "abbr", "cite", "q", "time",
    # 媒体与图文
    "img", "figure", "figcaption", "picture", "source",
    # 折叠块
    "details", "summary",
    # 任务列表的包裹：Tiptap 与 mdit 的 tasklists 都产出 `<label><input …></label>`。
    # 少了它，`<label>` 会被当未知标签**整棵丢弃**，里面的勾选框也一起没了。
    "label",
})

#: 所有标签都允许的属性
#:
#: `class` 与 `data-*` 是**刻意放行**的：富文本编辑器（Tiptap）靠它们表达语义 ——
#: 代码块的语言在 `class="language-x"`（前端 `lib/highlight.ts` 据此做语法高亮）、
#: 提示块在 `data-callout`。二者都无法执行代码，风险面仅限于样式层面的欺骗。
#: （`data-*` 在前缀判断里放行，不逐个枚举。）
GLOBAL_ATTRS = frozenset({"title", "dir", "lang", "id", "class"})

#: 每标签的额外属性（键为小写标签名）
ALLOWED_ATTRS: dict[str, frozenset[str]] = {
    "a": frozenset({"href", "target", "rel"}),
    # 任务列表勾选框：只放行这三项（`formaction` 之类一律丢弃）
    "input": frozenset({"type", "checked", "disabled"}),
    "img": frozenset({"src", "alt", "width", "height", "loading", "decoding"}),
    "source": frozenset({"src", "srcset", "type", "media"}),
    "td": frozenset({"colspan", "rowspan", "headers"}),
    "th": frozenset({"colspan", "rowspan", "scope", "headers"}),
    "col": frozenset({"span"}),
    "colgroup": frozenset({"span"}),
    "ol": frozenset({"start", "type", "reversed"}),
    "li": frozenset({"value"}),
    "time": frozenset({"datetime"}),
    "details": frozenset({"open"}),
    "blockquote": frozenset({"cite"}),
    "label": frozenset({"for"}),
}

#: `href` / `src` 允许的协议与相对路径前缀
_SAFE_URL_PREFIXES = ("http://", "https://", "/", "./", "../", "#", "mailto:", "tel:")

#: 命中即拒绝整份输入（防实体扩展）
_FORBIDDEN_DECL_RE = re.compile(r"<!\s*(doctype|entity)\b", re.IGNORECASE)

#: 危险 URL 协议（先剥离空白与不可见字符再比对，防 `java\tscript:` 之类绕过）
_DANGEROUS_URL_RE = re.compile(r"^\s*(javascript|vbscript|data)\s*:", re.IGNORECASE)


class UnsafeHtmlError(ValueError):
    """输入包含不能安全处理的结构（如 DOCTYPE/ENTITY 声明）。"""


def _is_safe_url(value: str) -> bool:
    """URL 是否安全：拒绝危险协议，其余要求命中安全前缀。"""
    if _DANGEROUS_URL_RE.match(value or ""):
        return False
    lowered = (value or "").strip().lower()
    # 去掉控制字符再判断（`java\nscript:` 这类绕过）
    lowered = re.sub(r"[\x00-\x20]", "", lowered)
    if _DANGEROUS_URL_RE.match(lowered):
        return False
    return lowered.startswith(_SAFE_URL_PREFIXES)


def _filter_attrs(element: etree._Element) -> None:
    tag = (element.tag or "").lower()
    allowed = GLOBAL_ATTRS | ALLOWED_ATTRS.get(tag, frozenset())
    for name in list(element.attrib):
        lowered = name.lower()
        # `on*` 一律丢弃（不枚举具体事件名）；`style` 整体丢弃（省去解析 CSS 的坑）
        if lowered.startswith("on") or lowered == "style":
            del element.attrib[name]
            continue
        # `data-*` 放行：不能执行代码，而富文本的提示块等语义依赖它
        if lowered.startswith("data-"):
            continue
        if lowered not in allowed:
            del element.attrib[name]
            continue
        if lowered in ("href", "src", "srcset") and not _is_safe_url(element.attrib[name]):
            del element.attrib[name]


def _clean_subtree(element: etree._Element) -> None:
    """自底向上清理：未知标签整棵丢弃，已知标签过滤属性后继续向下。"""
    for child in list(element):
        if not isinstance(child.tag, str):  # 注释 / 处理指令
            element.remove(child)
            continue
        if (child.tag or "").lower() not in ALLOWED_TAGS:
            element.remove(child)  # 整棵子树一起丢掉
            continue
        _filter_attrs(child)
        _clean_subtree(child)


def sanitize_html(raw: str) -> str:
    """把一段 HTML 片段净化成安全子集。

    输入含 `DOCTYPE` / `ENTITY` 时抛 `UnsafeHtmlError`（调用方应据此拒绝或转义）。
    解析失败时退化为"整段转义"，绝不把未解析的原文直接放行。
    """
    if not raw:
        return ""
    if _FORBIDDEN_DECL_RE.search(raw):
        raise UnsafeHtmlError("正文包含 DOCTYPE/ENTITY 声明")

    try:
        wrapper = lxml_html.fragment_fromstring(raw, create_parent="div")
    except Exception:  # noqa: BLE001
        # 解析不了就不放行原文：整段转义（与 html=False 的效果一致）
        return lxml_html.escape(raw)

    _clean_subtree(wrapper)
    return "".join(
        etree.tostring(child, encoding="unicode", method="html") for child in wrapper
    )
