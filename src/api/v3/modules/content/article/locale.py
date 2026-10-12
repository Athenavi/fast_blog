"""locale 规范化、回退链与 ``Accept-Language`` 解析。

为什么不需要新表
================

``article_content`` 本来就是"**一行一语言**"（``article_content.language_code``），
API 也已接受 ``language_code`` 参数。因此多语言内容缺的不是存储，而是：

  1. **回退链**：请求 ``zh-CN`` 但只有 ``zh`` 的正文时，应按链回退而不是返回空；
  2. **locale 解析**：支持 ``?locale=`` 与 ``Accept-Language``，并统一大小写形态。

回退链形态：``zh-CN`` → ``zh`` → 默认语言。
"""

from typing import Iterable, List, Optional

#: 与 article service 的默认语言一致
DEFAULT_LOCALE = "zh-CN"

#: 常见语言别名（region → 主语言映射由 ``_primary`` 完成，这里只补特例）
_ALIASES = {
    "zh": "zh-CN",
    "zh-hans": "zh-CN",
    "zh-hant": "zh-TW",
    "en": "en",
}


def _primary(locale: str) -> str:
    """取主语言标签：``zh-CN`` → ``zh``"""
    return locale.split("-", 1)[0].lower()


def normalize_locale(raw: Optional[str], *, default: Optional[str] = None) -> str:
    """规范化 locale：``zh-cn`` → ``zh-CN``；空值返回 ``default``（未给则空串）。

    只做"大小写与常见别名"归一，不引入语言数据库 —— 未知标签原样返回主语言形态。
    """
    text = (raw or "").strip()
    if not text:
        return default or ""
    # 允许 ``en_US`` 这类写法
    text = text.replace("_", "-")
    parts = [part for part in text.split("-") if part]
    if not parts:
        return default or ""
    lowered = "-".join([parts[0].lower()] + [p.upper() for p in parts[1:]])
    return _ALIASES.get(lowered.lower(), lowered)


def fallback_chain(locale: Optional[str], *, default: str = DEFAULT_LOCALE) -> List[str]:
    """构建回退链（去重保序）：``zh-CN`` → ``['zh-CN', 'zh', 'zh-CN默认']``。

    规则：

      - 请求 ``zh-CN`` → ``['zh-CN', 'zh', default]``
      - 请求 ``zh``    → ``['zh', default]``
      - 请求空/默认    → ``[default]``
    """
    default_norm = normalize_locale(default, default=DEFAULT_LOCALE) or DEFAULT_LOCALE
    requested = normalize_locale(locale)

    chain: List[str] = []
    if requested:
        chain.append(requested)
        primary = _primary(requested)
        if primary != requested.lower():
            chain.append(primary)
    chain.append(default_norm)

    seen: set[str] = set()
    ordered: List[str] = []
    for item in chain:
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            ordered.append(item)
    return ordered


def parse_accept_language(header: Optional[str], *, limit: int = 5) -> List[str]:
    """解析 ``Accept-Language``：按 q 值降序返回规范化 locale 列表。

    不实现通配 ``*``（无意义）；q=0 表示显式拒绝，会被跳过。
    """
    text = (header or "").strip()
    if not text:
        return []

    parsed: List[tuple[float, int, str]] = []
    for index, item in enumerate(text.split(",")):
        piece = item.strip()
        if not piece:
            continue
        tag, _, params = piece.partition(";")
        quality = 1.0
        for param in params.split(";"):
            key, _, value = param.strip().partition("=")
            if key.lower() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        tag = tag.strip()
        if not tag or tag == "*" or quality <= 0:
            continue
        normalized = normalize_locale(tag)
        if normalized:
            # ``-index`` 让同 q 值时保持原始顺序（稳定排序）
            parsed.append((-quality, index, normalized))

    parsed.sort()
    ordered: List[str] = []
    for _, _, locale in parsed[:limit]:
        if locale not in ordered:
            ordered.append(locale)
    return ordered


def resolve_requested_locale(
    explicit: Optional[str],
    accept_language: Optional[str],
    *,
    default: str = DEFAULT_LOCALE,
) -> List[str]:
    """确定"要按哪条链找正文"：显式 ``locale`` 优先，其次 ``Accept-Language``，最后默认。

    返回候选链（去重保序）。**注意顺序**：无显式 locale 时，链首必须是
    ``Accept-Language`` 里 q 值最高的语言（而不是默认语言），否则客户端拿到的
    永远是默认语言，Accept-Language 形同虚设；默认语言只作为链尾兜底。

    例：``Accept-Language: ja;q=0.9, zh-CN;q=0.2`` → ``['ja', 'zh-CN', 'zh']``。
    """
    if explicit:
        return fallback_chain(explicit, default=default)

    chain: List[str] = []
    for candidate in parse_accept_language(accept_language):
        for item in fallback_chain(candidate, default=default):
            if item not in chain:
                chain.append(item)

    default_norm = normalize_locale(default, default=DEFAULT_LOCALE) or DEFAULT_LOCALE
    if not chain:
        return [default_norm]
    if default_norm not in chain:
        chain.append(default_norm)
    return chain


def pick_locale(available: Iterable[Optional[str]], chain: Iterable[str]) -> Optional[str]:
    """从"已有语言集合"里按链挑第一个命中的语言；都不命中返回 ``None``。

    语言比较大小写不敏感（``zh-cn`` 与 ``zh-CN`` 视为同一语言）。
    """
    normalized = {}
    for item in available:
        if not item:
            continue
        normalized.setdefault(str(item).lower(), str(item))
    for candidate in chain:
        hit = normalized.get(candidate.lower())
        if hit:
            return hit
    return None
