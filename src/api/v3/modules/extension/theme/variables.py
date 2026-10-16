"""主题 settings → CSS 变量块（纯函数）

## 为什么需要这一步

主题的 `theme.json` 里有 `settings.colors.primary` 之类的配置项，后台也能改；
但 `styles.css` 是**静态文件** —— 改了配置不影响外观，配置项就成了摆设。
"配置项改了不生效"正是假实现的典型形态。

这里把 `settings` 渲染成 `:root { --color-primary: …; }` 变量块，与主题 CSS 一起下发；
主题 CSS 只引用变量、不写死颜色。于是"改配置 → 立即生效"才是真的。

## 为什么用白名单而不是全量透传

只渲染**已知的、有 CSS 变量对应**的设置项：

  - 值来自后台表单，虽经后端校验，但直接拼进 `<style>` 仍是注入面；
  - 主题可以新增任意 settings 键，全量透传会把它们变成不受控的 CSS 变量。

白名单让"能影响样式的键"是**可枚举、可审查**的；新键想生效必须在这里登记。
"""

from typing import Any, Dict, Optional

#: `settings.colors.*` → CSS 变量名
_COLOR_VARS: Dict[str, str] = {
    "primary": "--color-primary",
    "secondary": "--color-secondary",
    "accent": "--color-accent",
    "background": "--color-background",
    "foreground": "--color-foreground",
    "muted": "--color-muted",
    "border": "--color-border",
}

#: `settings.typography.*` → CSS 变量名
_TYPO_VARS: Dict[str, str] = {
    "fontFamily": "--font-family",
    "fontSize": "--font-size",
    "lineHeight": "--line-height",
    "headingFontWeight": "--heading-font-weight",
}

#: `settings.fontSizes.*` → CSS 变量名（字号尺度）
#:
#: 尺度本身是主题的表达（WP 用相对单位以利可访问性），所以不校验具体数值，
#: 只做与其余令牌同口径的注入防护。
_FONT_SIZE_VARS: Dict[str, str] = {
    "sm": "--text-sm",
    "base": "--text-base",
    "lg": "--text-lg",
    "xl": "--text-xl",
    "2xl": "--text-2xl",
}

#: `settings.spacing.*` → CSS 变量名（**8px 基础网格**，WP 现代设计系统的核心）
#:
#: 常用刻度：4（半格）/ 8 / 16 / 24 / 32 / 48 / 64。
_SPACING_VARS: Dict[str, str] = {
    "xs": "--space-xs",
    "sm": "--space-sm",
    "md": "--space-md",
    "lg": "--space-lg",
    "xl": "--space-xl",
    "2xl": "--space-2xl",
    "3xl": "--space-3xl",
}

#: `settings.focus.*` → CSS 变量名
#:
#: WP 规范要求焦点**清晰可见**（WCAG 2.4.13：轮廓至少 2px、对比度 ≥3:1）。
#: 这里只透传主题**显式声明**的值，不提供默认色：焦点色应结合主题主色决定，
#: 后端强塞一个颜色反而会与主题撞色、甚至跌破对比度要求。
_FOCUS_VARS: Dict[str, str] = {
    "width": "--focus-width",
    "offset": "--focus-offset",
    "color": "--focus-color",
}

#: `settings.motion.*` → CSS 变量名（WP 动效 100–200ms、简单缓动）
#:
#: 主题在 CSS 里引用它做过渡；**减少动效**由样式层用
#: `@media (prefers-reduced-motion: reduce)` 兜底，不靠这里。
_MOTION_VARS: Dict[str, str] = {
    "duration": "--motion-duration",
    "easing": "--motion-easing",
}

#: `settings.components.*` → CSS 变量名（值可直接透传的项）
_COMPONENT_VARS: Dict[str, str] = {
    "borderRadius": "--radius",
}

#: `settings.components.*` 里**取值为枚举**的项 → (CSS 变量名, 枚举映射)
#
# 这些项的值（`medium` / `pill`）本身不是合法 CSS，必须映射成真实值。
# 映射放在这里而不是让各主题自己处理：枚举到 CSS 的对应关系属于**主题契约**，
# 集中在后端能保证三个主题行为一致，也便于审查（与白名单同一考虑）。
_ENUM_COMPONENT_VARS: Dict[str, tuple] = {
    "shadowStyle": (
        "--shadow",
        {
            "none": "none",
            "small": "0 1px 2px rgb(0 0 0 / 0.05)",
            "medium": "0 4px 12px rgb(0 0 0 / 0.08)",
            "large": "0 12px 32px rgb(0 0 0 / 0.12)",
        },
    ),
    "buttonStyle": (
        "--button-radius",
        {
            "default": "0.5rem",
            "rounded": "0.75rem",
            "pill": "9999px",
        },
    ),
}

#: 出现这些片段即丢弃该值 —— CSS 里它们能提前闭合声明块或开启注释
_UNSAFE_TOKENS = (";", "{", "}", "/*", "*/", "<", ">", "\\")

#: 单个值长度上限（正常颜色/长度/字体栈远小于此）
_MAX_VALUE_LENGTH = 200


def _safe_value(value: Any) -> Optional[str]:
    """把设置值转成可安全放进 CSS 的字符串；不安全或为空则返回 None

    `bool` 显式排除：Python 里 `True` 会变成字符串 `"True"`，那不是合法的 CSS 值，
    而且布尔项本来就该由主题用类名/属性表达，不该变成变量。
    """
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text or len(text) > _MAX_VALUE_LENGTH:
        return None
    if any(token in text for token in _UNSAFE_TOKENS):
        return None
    return text


def _collect_enums(group: Any, lines: list) -> None:
    """把枚举型设置项映射成 CSS 变量（纯函数，就地追加）

    值不在映射表里时**跳过**，而不是把原值透传 —— 透传 `medium` 这种非 CSS 值
    会让该变量失效，排查起来反而更难。
    """
    if not isinstance(group, dict):
        return
    for key, (css_var, mapping) in _ENUM_COMPONENT_VARS.items():
        raw = group.get(key)
        if raw is None or isinstance(raw, bool):
            continue
        mapped = mapping.get(str(raw).strip())
        if mapped is not None:
            lines.append(f"  {css_var}: {mapped};")


def render_theme_variables(settings: Optional[Dict[str, Any]]) -> str:
    """把主题 settings 渲染成 ``:root { … }`` 块（纯函数）

    没有可用设置时返回**空串**（调用方据此不注入任何样式），
    而不是注入一个空的 ``:root {}`` —— 空规则块只会让 HTML 更难读。
    """
    if not isinstance(settings, dict):
        return ""

    lines: list[str] = []

    def collect(group: Any, mapping: Dict[str, str]) -> None:
        if not isinstance(group, dict):
            return
        for key, css_var in mapping.items():
            safe = _safe_value(group.get(key))
            if safe is not None:
                lines.append(f"  {css_var}: {safe};")

    collect(settings.get("colors"), _COLOR_VARS)
    collect(settings.get("typography"), _TYPO_VARS)
    collect(settings.get("fontSizes"), _FONT_SIZE_VARS)
    collect(settings.get("spacing"), _SPACING_VARS)
    collect(settings.get("focus"), _FOCUS_VARS)
    collect(settings.get("motion"), _MOTION_VARS)
    collect(settings.get("components"), _COMPONENT_VARS)
    _collect_enums(settings.get("components"), lines)

    if not lines:
        return ""
    return ":root {\n" + "\n".join(lines) + "\n}\n"
