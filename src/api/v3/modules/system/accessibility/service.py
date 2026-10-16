"""无障碍（WCAG 2.1）：配置持久化 + CSS / ARIA 生成 + HTML 规则校验

v2 的 ``shared/services/system/accessibility_service.py``（12.2KB）有两个问题：

1. **配置存在内存字典**里（代码注释自承"实际应该保存到数据库"）→ v3 落 ``system_settings``；
2. **校验只有 4 条粗糙规则**，且都是"整篇文本里有没有某个子串"的判断（``'<img' in html and
   'alt=' not in html``）—— 一张图缺 alt、另一张有 alt 就会漏报 → v3 换成**按元素解析**的规则集
   （``html.parser`` 收集标签，逐元素判定），并给出规则名、严重级别与定位信息。

CSS / ARIA / 跳过链接 / 键盘快捷键这些**纯生成**部分沿用 v2 的产出（它们本来就是对的），
由 v3 按当前配置组装成可注入前台的样式表。
"""

import json
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger

logger = get_logger("system.accessibility")

#: 配置在 ``system_settings`` 里的键
CONFIG_KEY = "accessibility.config"

#: 默认配置（键与 v2 一致）
DEFAULT_CONFIG: Dict[str, Any] = {
    "keyboard_navigation": True,
    "screen_reader_support": True,
    "high_contrast_mode": False,
    "font_size": "medium",
    "reduce_motion": False,
    "focus_visible": True,
    "skip_links": True,
}

#: 允许的字号档位 → 根字号
FONT_SIZE_PX: Dict[str, str] = {
    "small": "14px",
    "medium": "16px",
    "large": "18px",
    "x-large": "20px",
}

#: 允许的 ARIA 角色（校验用，覆盖常用的即可）
KNOWN_ROLES = frozenset(
    """
    alert alertdialog application article banner button cell checkbox columnheader combobox
    complementary contentinfo definition dialog directory document feed figure form grid
    gridcell group heading img link list listbox listitem log main marquee math menu menubar
    menuitem menuitemcheckbox menuitemradio navigation none note option presentation
    progressbar radio radiogroup region row rowgroup rowheader scrollbar search searchbox
    separator slider spinbutton status switch tab table tablist tabpanel term textbox timer
    toolbar tooltip tree treegrid treeitem
    """.split()
)

#: 链接文本过泛的提示词
VAGUE_LINK_TEXTS = frozenset(
    {"点击这里", "这里", "更多", "详情", "阅读更多", "click here", "here", "more", "read more", "link"}
)

#: 不需要 label 的 input 类型
SKIP_LABEL_INPUT_TYPES = frozenset({"hidden", "submit", "button", "reset", "image"})


def _text_of(attrs: Dict[str, str]) -> str:
    return (attrs.get("aria-label") or attrs.get("title") or "").strip()


#: 自闭合标签（不进栈）
VOID_TAGS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)


class _ElementCollector(HTMLParser):
    """收集需要校验的元素（比"整篇子串判断"可靠）

    每个元素一条记录 ``{"tag", "attrs", "text"}``；``text`` 是开标签到闭标签之间的文本，
    用来判断链接 / 按钮是否有可访问名称。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        self._stack: List[Dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        record: Dict[str, Any] = {
            "tag": tag.lower(),
            "attrs": {key.lower(): (value or "") for key, value in attrs},
            "text": [],
        }
        if record["attrs"].get("id"):
            self.ids.append(record["attrs"]["id"])
        self.elements.append(record)
        if record["tag"] not in VOID_TAGS:
            self._stack.append(record)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if self._stack and self._stack[-1]["tag"] == tag.lower():
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        for record in self._stack:
            record["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index]["tag"] == tag.lower():
                self._stack.pop(index)
                break

    @staticmethod
    def text_of(record: Dict[str, Any]) -> str:
        return " ".join("".join(record["text"]).split())


class AccessibilityService:
    """无障碍配置 / 生成 / 校验"""

    # ------------------------------------------------------------------ 配置
    async def get_config(self, db: AsyncSession) -> Dict[str, Any]:
        from shared.models.system.system_settings import SystemSettings

        row = (
            await db.execute(
                select(SystemSettings).where(SystemSettings.setting_key == CONFIG_KEY).limit(1)
            )
        ).scalars().first()
        stored: Dict[str, Any] = {}
        if row is not None and row.setting_value:
            try:
                parsed = json.loads(row.setting_value)
            except ValueError:
                logger.warning("无障碍配置不是合法 JSON，按默认值处理：%s", row.setting_value[:80])
                parsed = None
            if isinstance(parsed, dict):
                stored = parsed
        return {**DEFAULT_CONFIG, **{k: v for k, v in stored.items() if k in DEFAULT_CONFIG}}

    async def save_config(
        self, db: AsyncSession, payload: Dict[str, Any], *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """保存配置到 ``system_settings``（未知键与非法字号直接 400）"""
        from shared.models.system.system_settings import SystemSettings

        unknown = [key for key in payload if key not in DEFAULT_CONFIG]
        if unknown:
            raise BadRequestError(
                f"未知配置项：{unknown}（可选：{sorted(DEFAULT_CONFIG)}）"
            )
        if "font_size" in payload and payload["font_size"] not in FONT_SIZE_PX:
            raise BadRequestError(
                f"font_size 只支持 {sorted(FONT_SIZE_PX)}，收到「{payload['font_size']}」"
            )

        current = await self.get_config(db)
        merged = {**current, **{k: v for k, v in payload.items() if k in DEFAULT_CONFIG}}

        row = (
            await db.execute(
                select(SystemSettings).where(SystemSettings.setting_key == CONFIG_KEY).limit(1)
            )
        ).scalars().first()
        now = datetime.now()
        value = json.dumps(merged, ensure_ascii=False)
        if row is None:
            db.add(
                SystemSettings(
                    setting_key=CONFIG_KEY,
                    setting_value=value,
                    setting_type="json",
                    description="无障碍（WCAG）配置",
                    is_public=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.setting_value = value
            row.setting_type = "json"
            row.is_public = True
            row.updated_at = now
        await db.commit()
        logger.info("无障碍配置已更新（用户 %s）：%s", user_id, sorted(payload))
        return merged

    # ------------------------------------------------------------------ 生成
    @staticmethod
    def skip_links() -> List[Dict[str, str]]:
        return [
            {"id": "skip-to-main", "text": "跳到主要内容", "target": "#main-content",
             "aria_label": "Skip to main content"},
            {"id": "skip-to-nav", "text": "跳到导航", "target": "#main-navigation",
             "aria_label": "Skip to navigation"},
            {"id": "skip-to-search", "text": "跳到搜索", "target": "#search-form",
             "aria_label": "Skip to search"},
            {"id": "skip-to-footer", "text": "跳到底部", "target": "#footer",
             "aria_label": "Skip to footer"},
        ]

    @staticmethod
    def keyboard_shortcuts() -> List[Dict[str, str]]:
        return [
            {"keys": "Tab", "action": "聚焦下一个可交互元素"},
            {"keys": "Shift+Tab", "action": "聚焦上一个可交互元素"},
            {"keys": "Enter / Space", "action": "激活按钮或链接"},
            {"keys": "Esc", "action": "关闭弹窗 / 菜单"},
            {"keys": "/", "action": "聚焦站内搜索"},
            {"keys": "Alt+1", "action": "跳到主要内容"},
            {"keys": "Alt+2", "action": "跳到导航"},
            {"keys": "Alt+H", "action": "打开无障碍说明"},
        ]

    @staticmethod
    def aria_labels(element_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """常用元素类型的 ARIA 属性建议（``context`` 可覆盖默认标签）"""
        context = context or {}
        table: Dict[str, Dict[str, str]] = {
            "button": {"role": "button"},
            "link": {"role": "link"},
            "navigation": {"role": "navigation", "aria_label": context.get("label", "主导航")},
            "search": {"role": "search", "aria_label": context.get("label", "站内搜索")},
            "form": {"role": "form", "aria_labelledby": context.get("labelledby", "form-title")},
            "dialog": {"role": "dialog", "aria_modal": "true"},
            "tab": {"role": "tab", "aria_selected": "false"},
            "alert": {"role": "alert", "aria_live": "assertive"},
            "progressbar": {"role": "progressbar", "aria_valuemin": "0", "aria_valuemax": "100"},
            "menu": {"role": "menu", "aria_orientation": "vertical"},
        }
        result = table.get(element_type)
        if result is None:
            raise BadRequestError(
                f"不支持的元素类型「{element_type}」（可选：{sorted(table)}）"
            )
        return dict(result)

    @staticmethod
    def css(config: Dict[str, Any]) -> str:
        """按当前配置生成可注入前台的样式表"""
        merged = {**DEFAULT_CONFIG, **config}
        blocks: List[str] = ["/* 无障碍样式（按当前配置生成） */"]

        blocks.append(
            f":root {{ --a11y-font-size: {FONT_SIZE_PX.get(merged['font_size'], '16px')}; }}\n"
            "html { font-size: var(--a11y-font-size); }"
        )
        if merged["high_contrast_mode"]:
            blocks.append(
                """
.high-contrast {
  --bg-color: #000000; --text-color: #ffffff; --link-color: #ffff00;
  --border-color: #ffffff; --focus-color: #00ff00;
}
.high-contrast body { background-color: var(--bg-color) !important; color: var(--text-color) !important; }
.high-contrast a { color: var(--link-color) !important; text-decoration: underline !important; }
.high-contrast img { border: 2px solid var(--border-color) !important; }
.high-contrast .btn { border: 2px solid var(--border-color) !important; }
.high-contrast :focus-visible { outline-color: var(--focus-color) !important; }
""".strip()
            )
        if merged["focus_visible"]:
            blocks.append(
                """
:focus-visible { outline: 3px solid #00a0ff; outline-offset: 2px; }
""".strip()
            )
        if merged["reduce_motion"]:
            blocks.append(
                """
@media (prefers-reduced-motion: reduce), (min-width: 0px) {
  * { animation-duration: 0.001ms !important; animation-iteration-count: 1 !important;
      transition-duration: 0.001ms !important; scroll-behavior: auto !important; }
}
""".strip()
            )
        if merged["skip_links"]:
            blocks.append(
                """
.skip-link { position: absolute; left: -9999px; top: 0; z-index: 9999;
  background: #ffffff; color: #000000; padding: 8px 12px; }
.skip-link:focus { left: 8px; top: 8px; }
""".strip()
            )
        if merged["screen_reader_support"]:
            blocks.append(
                """
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
""".strip()
            )
        return "\n\n".join(blocks) + "\n"

    # ------------------------------------------------------------------ 校验
    def validate(self, html_content: str) -> Dict[str, Any]:
        """按元素解析的无障碍校验（规则名 + 严重级别 + 定位片段）"""
        if not (html_content or "").strip():
            raise BadRequestError("待校验的 HTML 为空")

        collector = _ElementCollector()
        collector.feed(html_content)

        errors: List[Dict[str, str]] = []
        warnings: List[Dict[str, str]] = []
        infos: List[Dict[str, str]] = []

        def add(bucket: List[Dict[str, str]], rule: str, message: str, severity: str, snippet: str = "") -> None:
            bucket.append({"rule": rule, "message": message, "severity": severity, "snippet": snippet[:80]})

        label_targets = {
            record["attrs"].get("for", "")
            for record in collector.elements
            if record["tag"] == "label" and record["attrs"].get("for")
        }
        heading_levels: List[int] = []
        has_main_anchor = False

        for record in collector.elements:
            tag, attrs = record["tag"], record["attrs"]
            content = collector.text_of(record)
            if tag == "html" and not attrs.get("lang"):
                add(errors, "html-lang", "html 元素缺少 lang 属性", "serious", str(attrs))
            elif tag == "img" and "alt" not in attrs:
                add(errors, "img-alt", "图片缺少 alt 属性（装饰图请写 alt=\"\"）", "critical", attrs.get("src", ""))
            elif tag == "button" and not content and not _text_of(attrs):
                add(errors, "button-name", "按钮没有可访问名称（文本或 aria-label）", "critical", str(attrs))
            elif tag == "a":
                if not content and not _text_of(attrs):
                    add(errors, "link-name", "链接没有可访问名称（文本或 aria-label）", "serious", attrs.get("href", ""))
                elif content.strip().lower() in VAGUE_LINK_TEXTS:
                    add(warnings, "link-text-vague", f"链接文本「{content.strip()}」含义不清", "moderate",
                        attrs.get("href", ""))
                if attrs.get("href", "").endswith("#main-content"):
                    has_main_anchor = True
            elif tag == "input":
                input_type = (attrs.get("type") or "text").lower()
                if input_type not in SKIP_LABEL_INPUT_TYPES:
                    has_label = (
                        bool(_text_of(attrs))
                        or bool(attrs.get("aria-labelledby"))
                        or bool(attrs.get("id") and attrs["id"] in label_targets)
                    )
                    if not has_label:
                        add(warnings, "form-label", "表单控件缺少关联的 label / aria-label", "moderate",
                            attrs.get("name", ""))
            elif tag == "iframe" and not attrs.get("title"):
                add(warnings, "iframe-title", "iframe 缺少 title", "moderate", attrs.get("src", ""))
            elif tag in ("video", "audio") and "autoplay" in attrs and "muted" not in attrs:
                add(warnings, "media-autoplay", "自动播放的媒体没有静音（会干扰屏幕阅读器）", "moderate", tag)
            elif tag == "table":
                if not any(item["tag"] == "th" for item in collector.elements):
                    add(warnings, "table-headers", "表格没有 th 表头", "moderate", "")
            elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                heading_levels.append(int(tag[1]))
            if attrs.get("tabindex", "").lstrip("+-").isdigit() and int(attrs["tabindex"]) > 0:
                add(warnings, "positive-tabindex", "tabindex 为正数会打乱 Tab 顺序", "moderate", attrs["tabindex"])
            role = (attrs.get("role") or "").strip().lower()
            if role and role not in KNOWN_ROLES:
                add(warnings, "aria-role-valid", f"未知的 role「{role}」", "minor", role)

        duplicates = [value for value, count in Counter(collector.ids).items() if count > 1]
        if duplicates:
            add(errors, "duplicate-id", f"存在重复 id：{duplicates[:5]}", "serious", ", ".join(duplicates[:5]))

        if not heading_levels:
            add(warnings, "heading-hierarchy", "页面没有任何标题（h1-h6）", "moderate")
        else:
            if 1 not in heading_levels:
                add(warnings, "heading-hierarchy", "页面缺少 h1 标题", "moderate")
            for previous, current in zip(heading_levels, heading_levels[1:]):
                if current - previous > 1:
                    add(warnings, "heading-order", f"标题层级从 h{previous} 跳到 h{current}", "moderate")
                    break

        if not has_main_anchor:
            add(infos, "skip-link", "未发现跳到主内容的锚点（#main-content），建议提供跳过链接", "minor")

        # info 只是建议、不扣分；error 扣 15、warning 扣 5
        score = max(0, 100 - len(errors) * 15 - len(warnings) * 5)
        return {
            "valid": not errors,
            "score": score,
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
            "summary": {
                "errors": len(errors),
                "warnings": len(warnings),
                "infos": len(infos),
                "elements_checked": len(collector.elements),
            },
        }

    # ------------------------------------------------------------------ 指南
    @staticmethod
    def guide() -> Dict[str, Any]:
        return {
            "standard": "WCAG 2.1 AA",
            "features": [
                {"key": "keyboard_navigation", "label": "键盘导航", "hint": "Tab / Shift+Tab 可遍历所有可交互元素"},
                {"key": "screen_reader_support", "label": "屏幕阅读器", "hint": "提供 .sr-only 与 ARIA 标签"},
                {"key": "high_contrast_mode", "label": "高对比度", "hint": "黑底白字、链接高亮，适合弱视用户"},
                {"key": "font_size", "label": "字号", "hint": f"可选 {sorted(FONT_SIZE_PX)}"},
                {"key": "reduce_motion", "label": "减少动效", "hint": "关闭动画与过渡，避免前庭不适"},
                {"key": "focus_visible", "label": "焦点可见", "hint": "键盘焦点有清晰轮廓"},
                {"key": "skip_links", "label": "跳过链接", "hint": "快速跳到主内容 / 导航 / 搜索"},
            ],
            "shortcuts": AccessibilityService.keyboard_shortcuts(),
            "skip_links": AccessibilityService.skip_links(),
        }


accessibility_service = AccessibilityService()
