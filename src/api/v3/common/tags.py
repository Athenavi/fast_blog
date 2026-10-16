"""标签值归一化（article 与 tag 模块共用）

``articles.tags_list`` 是 JSON 列，历史数据里出现过三种形态：
``["a","b"]``、``"a,b"``、``[{"name":"a"}]``，统一在这里归一，避免各模块各写一遍。
"""

from typing import Any, List


def normalize_tags(value: Any) -> List[str]:
    """把任意形态的标签值归一成去重后的字符串列表（保持原顺序）"""
    names: List[str] = []

    if value is None:
        raw: List[Any] = []
    elif isinstance(value, str):
        raw = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = [value]

    for item in raw:
        if item is None:
            continue
        if isinstance(item, dict):
            item = item.get("name") or item.get("title") or item.get("slug")
        if item is None:
            continue
        name = str(item).strip()
        if name and name not in names:
            names.append(name)
    return names
