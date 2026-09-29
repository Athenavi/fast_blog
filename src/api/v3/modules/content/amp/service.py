"""AMP（Accelerated Mobile Pages）：真实的正文 → AMP HTML 转换器 + 规范校验

v2 的 ``shared/services/advanced_features/amp_service.py`` 有两处「看似能用、实则脆弱」的实现：

1. **用正则做 HTML 改写**（``re.sub(r'<img\\s+([^>]*)src=...')``、``re.sub(r'\\son\\w+\\s*=...')``）——
   遇到属性顺序变化、属性里含 ``>``、布尔属性、嵌套标签就会漏改或改坏；而且它把整篇文档当字符串拼，
   无法知道正文里到底有哪些元素；
2. **CSS 限额硬编码成 50KB**、校验里对 ``script`` 直接放行（其实只有 AMP runtime / 组件 /
   ``application/ld+json`` 的 ``<script>`` 才合法）。

v3 换成 **基于 ``html.parser`` 的元素级转换器**：

  - 逐标签处理：``<img>`` → ``<amp-img>``、``<video>`` → ``<amp-video>``、``<audio>`` → ``<amp-audio>``；
  - 剥离禁用标签（``script`` / ``iframe`` / ``form`` / ``input`` … 整棵子树）与内联事件属性（``on*``）；
  - 收集正文里的 ``<style>`` 合并进 ``<style amp-custom>``，按 **75KB**（AMP 规范上限）按字节截断；
  - 生成 canonical、boilerplate、runtime / 组件脚本、``application/ld+json`` 结构化数据；
  - ``validate_amp`` 返回**违规项**（禁用标签 / CSS 超限 / 缺 canonical / 缺 ``<html amp>`` 等）。

正文内容从真表读：``articles``（标题 / 封面 / 发布时间）+ ``article_content``（正文，按语言一行）
+ ``article_seo``（canonical / og_image），站点信息复用 ``analytics/seo`` 的 ``site_context``。
"""

import json
from collections import Counter
from datetime import datetime
from html import escape
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.article.article_seo import ArticleSEO
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("content.amp")

#: ``<style amp-custom>`` 的字节上限（AMP 规范：75KB）
CSS_LIMIT_BYTES = 75 * 1024

#: 允许的 AMP 脚本宿主（其余 ``<script>`` 视为违规）
ALLOWED_SCRIPT_HOST = "cdn.ampproject.org"

DEFAULT_SITE_NAME = "FastBlog"

#: 默认尺寸（原标签未给出 width/height 时使用）
DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT = "800", "600"
DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT = "640", "360"
DEFAULT_AUDIO_WIDTH, DEFAULT_AUDIO_HEIGHT = "640", "50"

#: 空元素（无需闭合；输出为自闭合）
VOID_TAGS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)

#: 转换阶段要**整棵子树移除**的标签
DISALLOWED_TAGS = frozenset(
    "script iframe form input button select textarea embed object applet "
    "frame frameset base link meta noscript".split()
)

#: 校验阶段视为违规的标签（``script`` 单独按 src/type 判定，不在此列）
FORBIDDEN_TAGS = frozenset(
    "iframe form input button select textarea embed object applet frame frameset".split()
)

#: 标签替换表
TAG_MAP = {"img": "amp-img", "video": "amp-video", "audio": "amp-audio"}

#: 这些映射后的 AMP 元素即便源自空元素也需要显式闭合
SELF_CLOSING_AMP = frozenset({"amp-img"})

#: 组件脚本（按正文里出现的 AMP 元素按需注入）
COMPONENT_SCRIPTS: Dict[str, str] = {
    "amp-img": '<script async custom-element="amp-img" '
               'src="https://cdn.ampproject.org/v0/amp-img-0.1.js"></script>',
    "amp-video": '<script async custom-element="amp-video" '
                 'src="https://cdn.ampproject.org/v0/amp-video-0.1.js"></script>',
    "amp-audio": '<script async custom-element="amp-audio" '
                 'src="https://cdn.ampproject.org/v0/amp-audio-0.1.js"></script>',
}

#: 基础样式（与 v2 观感一致，全部收进 ``<style amp-custom>``）
BASE_CSS = (
    "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,"
    "Ubuntu,Cantarell,sans-serif;line-height:1.6;color:#333;max-width:800px;"
    "margin:0 auto;padding:20px}"
    ".amp-header{margin-bottom:30px}"
    ".amp-title{font-size:2em;margin-bottom:10px}"
    ".amp-meta{color:#666;font-size:.9em}"
    ".amp-content{font-size:1.1em}"
    ".amp-content amp-img{max-width:100%}"
)

#: AMP boilerplate（规范要求，缺一不可）
AMP_BOILERPLATE = (
    "<style amp-boilerplate>body{-webkit-animation:-amp-start 8s steps(1,end) 0s 1 normal both;"
    "-moz-animation:-amp-start 8s steps(1,end) 0s 1 normal both;"
    "-ms-animation:-amp-start 8s steps(1,end) 0s 1 normal both;"
    "animation:-amp-start 8s steps(1,end) 0s 1 normal both}"
    "@-webkit-keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}"
    "@-moz-keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}"
    "@-ms-keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}"
    "@-o-keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}"
    "@keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}</style>"
    "<noscript><style amp-boilerplate>body{-webkit-animation:none;-moz-animation:none;"
    "-ms-animation:none;animation:none}</style></noscript>"
)

#: AMP runtime
AMP_RUNTIME = '<script async src="https://cdn.ampproject.org/v0.js"></script>'


def _start_markup(tag: str, attrs: Dict[str, Any]) -> str:
    """把标签名 + 属性字典渲染成开标签字符串（属性值转义）"""
    pieces = [tag]
    for name, value in attrs.items():
        if value is None:
            pieces.append(name)
        else:
            pieces.append(f'{name}="{escape(str(value), quote=True)}"')
    return "<" + " ".join(pieces) + ">"


def _dedupe(items: List[str]) -> List[str]:
    """去重但保持首次出现顺序"""
    seen: List[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


class _AmpBodyParser(HTMLParser):
    """逐元素把正文片段改写为 AMP 兼容片段

    维护输出缓冲 ``parts``、收集到的 CSS ``css_parts``、被移除的标签 ``removed``；
    用一个跳过栈 ``_skip`` 丢弃禁用标签的整棵子树，用 ``_in_style`` 收集 ``<style>`` 文本。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.css_parts: List[str] = []
        self.removed: List[str] = []
        self._skip: List[str] = []
        self._in_style = False

    # ------------------------------------------------------------------ 内部
    @staticmethod
    def _filter_attrs(attrs) -> Dict[str, Any]:
        """丢弃空名属性与内联事件属性（``on*``）"""
        result: Dict[str, Any] = {}
        for name, value in attrs:
            if not name:
                continue
            lowered = name.lower()
            if lowered.startswith("on"):
                continue
            result[lowered] = value
        return result

    @staticmethod
    def _amp_attrs(tag: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """为 AMP 媒体元素补全必需属性（width / height / layout）"""
        if tag == "amp-img":
            attrs.setdefault("width", DEFAULT_IMAGE_WIDTH)
            attrs.setdefault("height", DEFAULT_IMAGE_HEIGHT)
            attrs.setdefault("layout", "responsive")
            attrs.setdefault("alt", "")
        elif tag == "amp-video":
            attrs.setdefault("width", DEFAULT_VIDEO_WIDTH)
            attrs.setdefault("height", DEFAULT_VIDEO_HEIGHT)
            attrs.setdefault("layout", "responsive")
        elif tag == "amp-audio":
            attrs.setdefault("width", DEFAULT_AUDIO_WIDTH)
            attrs.setdefault("height", DEFAULT_AUDIO_HEIGHT)
            attrs.setdefault("layout", "fixed")
        return attrs

    def _emit_open(self, tag: str, attrs, *, selfclose: bool) -> None:
        mapped = TAG_MAP.get(tag, tag)
        filtered = self._amp_attrs(mapped, self._filter_attrs(attrs))
        markup = _start_markup(mapped, filtered)
        if selfclose or mapped in SELF_CLOSING_AMP:
            markup += f"</{mapped}>"
        self.parts.append(markup)

    # ------------------------------------------------------------------ 回调
    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if self._in_style:
            return  # <style> 内是 CSS 文本，不是结构
        if self._skip:
            if tag not in VOID_TAGS:
                self._skip.append(tag)
            return
        if tag == "style":
            self._in_style = True
            return
        if tag in DISALLOWED_TAGS:
            self.removed.append(tag)
            if tag not in VOID_TAGS:
                self._skip.append(tag)
            return
        self._emit_open(tag, attrs, selfclose=tag in VOID_TAGS)

    def handle_startendtag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if self._in_style or self._skip:
            return
        if tag == "style":
            return
        if tag in DISALLOWED_TAGS:
            self.removed.append(tag)
            return
        self._emit_open(tag, attrs, selfclose=True)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._in_style:
            if tag == "style":
                self._in_style = False
            return
        if self._skip:
            for index in range(len(self._skip) - 1, -1, -1):
                if self._skip[index] == tag:
                    del self._skip[index:]
                    break
            return
        self.parts.append(f"</{TAG_MAP.get(tag, tag)}>")

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.css_parts.append(data)
            return
        if self._skip:
            return
        self.parts.append(escape(data, quote=False))


def convert_html_fragment(html_content: str) -> Dict[str, Any]:
    """把一段 HTML 片段转成 AMP 兼容片段（纯函数，便于单测）

    返回 ``{"html", "css", "removed_tags"}``：``html`` 是改写后的正文片段，
    ``css`` 是正文内 ``<style>`` 收集到的样式，``removed_tags`` 是被移除的标签名（去重）。
    """
    parser = _AmpBodyParser()
    parser.feed(html_content or "")
    parser.close()
    return {
        "html": "".join(parser.parts).strip(),
        "css": "".join(parser.css_parts).strip(),
        "removed_tags": _dedupe(parser.removed),
    }


def limit_css(css: str, limit: int = CSS_LIMIT_BYTES) -> tuple:
    """按**字节**把 CSS 截断到 ``limit`` 以内（避免切在多字节字符中间）

    返回 ``(css, truncated)``。
    """
    data = css.encode("utf-8")
    if len(data) <= limit:
        return css, False
    marker = f"\n/* ...(CSS 超出 {limit // 1024}KB 上限，已截断) */\n"
    marker_bytes = marker.encode("utf-8")
    budget = max(limit - len(marker_bytes), 0)
    truncated = data[:budget].decode("utf-8", errors="ignore")
    return truncated + marker, True


def to_datetime(value: Any) -> Optional[datetime]:
    """把 datetime / ISO 字符串统一成 ``datetime``（无法解析返回 ``None``）"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        return None


class _AmpValidatorParser(HTMLParser):
    """收集校验所需的事实（不构造输出）"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_html = False
        self.html_attrs: Dict[str, str] = {}
        self.tags: List[str] = []
        self.scripts: List[Dict[str, str]] = []
        self.has_canonical = False
        self.has_charset = False
        self.has_viewport = False
        self.has_boilerplate = False
        self.event_attrs = 0
        self._in_custom = False
        self.amp_custom: List[str] = []

    def _handle(self, tag: str, attrs) -> None:
        tag = tag.lower()
        attrs_dict = {name.lower(): (value or "") for name, value in attrs}
        if any(name.startswith("on") for name in attrs_dict):
            self.event_attrs += 1
        self.tags.append(tag)
        if tag == "html":
            self.has_html = True
            self.html_attrs = attrs_dict
        elif tag == "link" and attrs_dict.get("rel", "").lower() == "canonical":
            self.has_canonical = True
        elif tag == "meta":
            if "charset" in attrs_dict:
                self.has_charset = True
            if attrs_dict.get("name", "").lower() == "viewport":
                self.has_viewport = True
        elif tag == "style":
            if "amp-custom" in attrs_dict:
                self._in_custom = True
            elif "amp-boilerplate" in attrs_dict:
                self.has_boilerplate = True
        elif tag == "script":
            self.scripts.append(attrs_dict)

    def handle_starttag(self, tag: str, attrs) -> None:
        self._handle(tag, attrs)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self._handle(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style":
            self._in_custom = False

    def handle_data(self, data: str) -> None:
        if self._in_custom:
            self.amp_custom.append(data)


class AmpService:
    """AMP 文档生成 + 规范校验"""

    # ------------------------------------------------------------------ 转换
    def render_document(
        self,
        *,
        title: str = "",
        content_html: str = "",
        author_name: str = "",
        published_at: Any = None,
        modified_at: Any = None,
        featured_image: str = "",
        canonical_url: str = "",
        site_name: str = DEFAULT_SITE_NAME,
        language: str = "zh-CN",
        extra_css: str = "",
    ) -> Dict[str, Any]:
        """把正文渲染成完整的 AMP 文档，并返回生成过程的事实"""
        fragment = convert_html_fragment(content_html)
        custom_css, truncated = limit_css(
            "\n".join(section for section in (BASE_CSS, fragment["css"], extra_css.strip()) if section)
        )

        # 组件脚本必须覆盖**文档里实际出现**的 AMP 组件：正文片段 + 封面图
        # （封面图的 <amp-img> 在下面 body 里无条件输出，漏掉它会让生成的文档缺组件脚本）
        used_components = {name for name in ("amp-img", "amp-video", "amp-audio") if f"<{name}" in fragment["html"]}
        if featured_image:
            used_components.add("amp-img")
        components = [name for name in ("amp-img", "amp-video", "amp-audio") if name in used_components]
        published = to_datetime(published_at)
        modified = to_datetime(modified_at) or published

        structured: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": title,
            "datePublished": published.isoformat() if published else None,
            "dateModified": modified.isoformat() if modified else None,
            "author": {"@type": "Person", "name": author_name or site_name},
            "publisher": {"@type": "Organization", "name": site_name},
        }
        if canonical_url:
            structured["mainEntityOfPage"] = canonical_url
        if featured_image:
            structured["image"] = [featured_image]
        structured = {key: value for key, value in structured.items() if value is not None}
        json_ld = json.dumps(structured, ensure_ascii=False).replace("</", "<\\/")

        head = [
            "<!doctype html>",
            f'<html amp lang="{escape(language, quote=True)}">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,minimum-scale=1,initial-scale=1">',
            f'<link rel="canonical" href="{escape(canonical_url, quote=True)}">',
            f"<title>{escape(title)}</title>",
            AMP_BOILERPLATE,
            AMP_RUNTIME,
        ]
        head.extend(COMPONENT_SCRIPTS[name] for name in components)
        head.append(f'<script type="application/ld+json">{json_ld}</script>')
        head.append(f"<style amp-custom>{custom_css}</style>")
        head.append("</head>")

        published_label = published.strftime("%Y-%m-%d") if published else ""
        body = [
            "<body>",
            "<article>",
            '<header class="amp-header">',
            f'<h1 class="amp-title">{escape(title)}</h1>',
            f'<div class="amp-meta"><span>作者：{escape(author_name)}</span>'
            f'<span>发布时间：{escape(published_label)}</span></div>',
            "</header>",
        ]
        if featured_image:
            body.append(
                f'<amp-img src="{escape(featured_image, quote=True)}" width="800" height="450" '
                f'layout="responsive" alt="{escape(title, quote=True)}"></amp-img>'
            )
        body.extend(['<div class="amp-content">', fragment["html"], "</div>"])
        body.extend(["</article>", "</body>", "</html>"])

        document = "\n".join(head + body)
        return {
            "html": document,
            "css": custom_css,
            "css_bytes": len(custom_css.encode("utf-8")),
            "css_limit": CSS_LIMIT_BYTES,
            "css_truncated": truncated,
            "components": components,
            "removed_tags": fragment["removed_tags"],
            "canonical_url": canonical_url,
        }

    def build_document(self, **kwargs: Any) -> str:
        """``render_document`` 的便捷封装，只取文档字符串"""
        return self.render_document(**kwargs)["html"]

    def convert_to_amp(
        self,
        *,
        html: str,
        title: str = "",
        author_name: str = "",
        canonical_url: str = "",
        site_name: str = DEFAULT_SITE_NAME,
        featured_image: str = "",
        published_at: Any = None,
        extra_css: str = "",
    ) -> Dict[str, Any]:
        """把任意 HTML 转成 AMP 文档，并附带自检结果（``POST /amp/convert``）"""
        if not (html or "").strip():
            raise BadRequestError("待转换的 HTML 为空")
        rendered = self.render_document(
            title=title,
            content_html=html,
            author_name=author_name,
            published_at=published_at,
            featured_image=featured_image,
            canonical_url=canonical_url,
            site_name=site_name or DEFAULT_SITE_NAME,
            extra_css=extra_css,
        )
        return {
            "amp_html": rendered["html"],
            "canonical_url": rendered["canonical_url"],
            "components": rendered["components"],
            "removed_tags": rendered["removed_tags"],
            "css": {
                "bytes": rendered["css_bytes"],
                "limit": rendered["css_limit"],
                "truncated": rendered["css_truncated"],
            },
            "validation": self.validate_amp(rendered["html"]),
        }

    # ------------------------------------------------------------------ 校验
    def validate_amp(self, html_content: str) -> Dict[str, Any]:
        """返回 AMP 规范**违规项**（禁用标签 / CSS 超限 / 缺 canonical / 缺 ``<html amp>`` …）"""
        if not (html_content or "").strip():
            raise BadRequestError("待校验的 HTML 为空")

        parser = _AmpValidatorParser()
        parser.feed(html_content)
        parser.close()

        errors: List[Dict[str, str]] = []
        warnings: List[Dict[str, str]] = []

        def err(rule: str, message: str) -> None:
            errors.append({"rule": rule, "message": message})

        def warn(rule: str, message: str) -> None:
            warnings.append({"rule": rule, "message": message})

        if not parser.has_html or not any(key in ("amp", "⚡") for key in parser.html_attrs):
            err("missing-amp-attribute", "<html> 缺少 amp（或 ⚡）属性")
        if not parser.has_charset:
            err("missing-charset", '缺少 <meta charset="utf-8">')
        if not parser.has_viewport:
            err("missing-viewport", "缺少 viewport meta 标签")
        if not parser.has_canonical:
            err("missing-canonical", '缺少 <link rel="canonical">')
        if not parser.has_boilerplate:
            warn("missing-boilerplate", "缺少 AMP boilerplate 样式")
        if parser.event_attrs:
            err("inline-event-handler", f"存在 {parser.event_attrs} 个内联事件属性（on*）")

        forbidden = Counter(tag for tag in parser.tags if tag in FORBIDDEN_TAGS)
        for tag, count in forbidden.items():
            err("forbidden-tag", f"存在禁用标签 <{tag}> ×{count}")

        img_tags = [tag for tag in parser.tags if tag == "img"]
        if img_tags:
            warn("use-amp-img", f"存在 {len(img_tags)} 个未转换为 <amp-img> 的 <img> 标签")

        for attrs in parser.scripts:
            src = attrs.get("src", "")
            script_type = attrs.get("type", "").lower()
            if ALLOWED_SCRIPT_HOST in src or script_type in ("application/ld+json", "application/json"):
                continue
            err("forbidden-script", f"不允许的 <script>（src/type：{src or script_type or 'inline'}）")

        css_bytes = len("".join(parser.amp_custom).encode("utf-8"))
        if css_bytes > CSS_LIMIT_BYTES:
            err(
                "css-limit",
                f"<style amp-custom> 超出 {CSS_LIMIT_BYTES // 1024}KB 上限"
                f"（当前 {css_bytes / 1024:.1f}KB）",
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "errors": len(errors),
                "warnings": len(warnings),
                "css_bytes": css_bytes,
                "css_limit": CSS_LIMIT_BYTES,
                "elements_checked": len(parser.tags),
            },
        }

    # ------------------------------------------------------------------ 文章联动
    async def generate_for_article(self, db: AsyncSession, article_id: int) -> Dict[str, Any]:
        """从真表读文章并生成 AMP 文档（``GET /amp/article/{article_id}``）"""
        article = await db.get(Article, article_id)
        if article is None:
            raise NotFoundError("文章不存在")

        content_row = (
            await db.execute(
                select(ArticleContent)
                .where(ArticleContent.article == article_id)
                .order_by(ArticleContent.id.asc())
                .limit(1)
            )
        ).scalars().first()
        content_html = content_row.content if content_row is not None else ""

        seo = (
            await db.execute(
                select(ArticleSEO).where(ArticleSEO.article_id == article_id).limit(1)
            )
        ).scalars().first()

        # 站点名 / 站点基址复用 analytics/seo 的 site_context（sites → system_settings → 默认）
        from src.api.v3.modules.analytics.seo.schema_org import schema_org_service

        context = await schema_org_service.site_context(db)
        base = context.get("base_url") or ""
        canonical = (
            (seo.canonical_url if seo is not None else None)
            or (f"{base}/article/{article.slug}" if base and article.slug else "")
        )

        author_name = await self._author_name(db, article.user)
        featured_image = (
            (seo.og_image if seo is not None else None)
            or article.cover_image
            or ""
        )
        published_at = article.published_at or article.created_at

        rendered = self.render_document(
            title=article.title or "",
            content_html=content_html or "",
            author_name=author_name,
            published_at=published_at,
            modified_at=article.updated_at,
            featured_image=featured_image,
            canonical_url=canonical,
            site_name=context.get("name") or DEFAULT_SITE_NAME,
        )
        validation = self.validate_amp(rendered["html"])
        logger.info("已生成 AMP 文档 article_id=%s 组件=%s", article_id, rendered["components"])
        return {
            "article_id": int(article.id),
            "title": article.title,
            "slug": article.slug,
            "canonical_url": canonical,
            "site": context,
            "components": rendered["components"],
            "removed_tags": rendered["removed_tags"],
            "css": {
                "bytes": rendered["css_bytes"],
                "limit": rendered["css_limit"],
                "truncated": rendered["css_truncated"],
            },
            "amp_html": rendered["html"],
            "validation": validation,
        }

    @staticmethod
    async def _author_name(db: AsyncSession, user_id: Any) -> str:
        if user_id in (None, ""):
            return ""
        from shared.models.user import User

        row = await db.get(User, int(user_id))
        if row is None:
            return ""
        return str(getattr(row, "nickname", None) or getattr(row, "username", "") or "")


amp_service = AmpService()
