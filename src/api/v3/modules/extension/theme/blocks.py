"""主题区块协议（L1 声明式页面）

## 为什么需要它

主题以前只能提供**编译期 Vue 组件**（`frontend/site/*.vue`），而 Vue SFC 必须编译 ——
换主题要重新构建，与「插件 = 热插拔」的目标冲突。

声明式区块把页面描述变成**纯数据**：后端随 bootstrap 下发，前端用内置渲染器解释执行。
**改 `theme.json` → 刷新即生效，零构建。**

## 协议

```json
{"block": "<name>", "props": {...}, "children": [ ... ]}
```

- `block` 必须在白名单内。未知区块**跳过并告警**，而不是整页报错：
  主题可能面向更新的版本，少一个区块远比白屏好。
- `children` 支持任意嵌套（用于 columns / section 这类容器），但有**深度与总量上限** ——
  防止主题写出病态结构拖垮前端渲染。
- `props` 的值做与主题变量**同口径**的校验（拒 `;{}/*<>`）：它们最终会进入模板。

## 为什么白名单放在后端

前端也会做一次校验（防御性），但**权威判定在后端**：这里是唯一能同时约束
"内置主题"与"第三方主题"的地方，也让区块集合成为**可枚举、可审查**的契约。
新增区块必须在这里登记，否则主题写了也不生效。
"""

from typing import Any, Dict, List, Optional, Tuple

#: 单个值长度上限（正常的文案/类名/尺寸远小于此）
_MAX_PROP_LENGTH = 200

#: 出现这些片段即丢弃该 prop 值 —— 它们能提前闭合标签或开启注释
_UNSAFE_TOKENS = (";", "{", "}", "/*", "*/", "<", ">", "\\")

#: 嵌套深度上限（含根层）
MAX_DEPTH = 6

#: 单个页面的区块总数上限
MAX_BLOCKS = 300

#: 允许的区块名 → 说明（说明只用于报错与文档，不参与渲染）
ALLOWED_BLOCKS: Dict[str, str] = {
    # 布局容器
    "section": "区块容器，可设 padding/背景/宽度",
    "columns": "多列容器（子节点成为列）",
    "container": "定宽内容容器",
    # 站点框架
    "site-header": "页头（站点名/导航/搜索）",
    "site-footer": "页脚",
    "site-nav": "主导航",
    "search-box": "搜索框",
    # 首页 / 列表
    "hero": "首屏标题区",
    "page-title": "页面标题",
    "post-list": "文章列表（limit/layout/columns/paginated/category）",
    "post-card": "单篇文章卡片",
    "category-nav": "分类导航",
    "tag-cloud": "标签云",
    "pagination": "分页",
    # 文章详情
    "post-header": "文章标题区",
    "post-meta": "文章元信息（作者/时间/阅读量）",
    "post-content": "文章正文（服务端已渲染并净化）",
    "post-tags": "文章标签",
    "post-related": "相关文章",
    "comment-list": "评论列表",
    # 通用
    "html": "一段受净化的富文本",
    "spacer": "垂直留白",
    # 侧栏与小工具（WP 经典主题的核心特征：主栏 + 右侧栏）
    "sidebar": "侧栏容器（语义 <aside>，屏幕阅读器可与正文区分）",
    "widget-categories": "分类小工具",
    "widget-tags": "标签云小工具",
    "widget-recent": "最新文章小工具",
}


def _safe_prop(value: Any) -> Optional[Any]:
    """把 prop 值规整为可安全渲染的类型；不安全则丢弃（返回 None）

    允许标量（str/int/float/bool/None）与**一层**列表（如 columns 的标签数组）；
    嵌套 dict 直接丢弃 —— 区块参数应当是扁平的，深层结构说明主题协议用错了。
    """
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text or len(text) > _MAX_PROP_LENGTH:
            return None
        if any(token in text for token in _UNSAFE_TOKENS):
            return None
        return text
    if isinstance(value, (list, tuple)):
        items = [_safe_prop(item) for item in value]
        cleaned = [item for item in items if item is not None]
        return cleaned or None
    return None


def _normalize_props(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    props: Dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            continue
        safe = _safe_prop(value)
        if safe is not None:
            props[key] = safe
    return props


def _normalize_node(raw: Any, depth: int, counter: List[int], warnings: List[str]) -> Optional[Dict[str, Any]]:
    """归一化单个区块节点（递归）；不可用时返回 None"""
    if not isinstance(raw, dict):
        return None

    name = raw.get("block")
    if not isinstance(name, str) or name not in ALLOWED_BLOCKS:
        if isinstance(name, str):
            warnings.append(f"未知区块 {name!r} 已跳过")
        return None

    counter[0] += 1
    if counter[0] > MAX_BLOCKS:
        return None

    node: Dict[str, Any] = {"block": name}

    props = _normalize_props(raw.get("props"))
    if props:
        node["props"] = props

    # 可选样式钩子：让主题给单个区块加类名（用于 styles.css 定向）
    cls = raw.get("class")
    if isinstance(cls, str) and cls.strip() and not any(t in cls for t in _UNSAFE_TOKENS):
        node["class"] = cls.strip()[:200]

    children_raw = raw.get("children")
    if isinstance(children_raw, (list, tuple)):
        if depth >= MAX_DEPTH:
            warnings.append(f"嵌套超过 {MAX_DEPTH} 层，{name!r} 的子区块已跳过")
        else:
            children: List[Dict[str, Any]] = []
            for child in children_raw:
                normalized = _normalize_node(child, depth + 1, counter, warnings)
                if normalized is not None:
                    children.append(normalized)
            if children:
                node["children"] = children

    return node


def normalize_templates(raw: Any) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str]]:
    """把 ``theme.json`` 的 ``templates`` 归一化并校验（纯函数）

    Returns:
        (templates, warnings)

        - ``templates``: ``{"HomePage": [ {block, props, children, class}, ... ]}``；
          无效或空页面不会出现在结果里；
        - ``warnings``: 被跳过的区块/超限说明，供日志与后台提示 —— **不抛异常**，
          主题写错一个区块不应该让整个站点 500。

    ``templates`` 缺失或不是 dict 时返回 ``({}, [])``，调用方据此回退到内置页面。
    """
    if not isinstance(raw, dict):
        return {}, []

    templates: Dict[str, List[Dict[str, Any]]] = {}
    warnings: List[str] = []

    for page_name, nodes in raw.items():
        if not isinstance(page_name, str) or not page_name.strip():
            continue
        if not isinstance(nodes, (list, tuple)):
            continue
        counter = [0]
        normalized_nodes: List[Dict[str, Any]] = []
        for node in nodes:
            normalized = _normalize_node(node, 1, counter, warnings)
            if normalized is not None:
                normalized_nodes.append(normalized)
        if normalized_nodes:
            templates[page_name.strip()] = normalized_nodes

    return templates, warnings
