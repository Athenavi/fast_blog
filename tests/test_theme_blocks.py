"""主题区块协议（L1 声明式页面）的校验测试

`src/api/v3/modules/extension/theme/blocks.py` 是主题页面结构的**唯一守门人**：
区块白名单、嵌套深度、区块总量、prop 注入防护。这些地方一旦被改坏，
后果是"主题写了不生效"或"主题能往页面里注入内容"，而且**不会有任何报错** ——
所以必须有测试锁定，不能只靠读代码。
"""

from src.api.v3.modules.extension.theme.blocks import (
    ALLOWED_BLOCKS,
    MAX_DEPTH,
    normalize_templates,
)


def test_valid_nested_templates_are_kept():
    """正常嵌套结构原样保留（block / props / class / children 都不丢）"""
    raw = {
        "HomePage": [
            {
                "block": "section",
                "props": {"padding": "lg"},
                "class": "wp-primary",
                "children": [
                    {"block": "post-list", "props": {"limit": 6, "layout": "list"}},
                ],
            }
        ]
    }
    templates, warnings = normalize_templates(raw)

    assert warnings == []
    assert list(templates) == ["HomePage"]

    node = templates["HomePage"][0]
    assert node["block"] == "section"
    assert node["props"] == {"padding": "lg"}
    assert node["class"] == "wp-primary"
    assert node["children"] == [{"block": "post-list", "props": {"limit": 6, "layout": "list"}}]


def test_unknown_block_is_skipped_with_warning():
    """未知区块**跳过并告警**，而不是整页报错（主题可能面向更新的版本）"""
    raw = {"HomePage": [{"block": "not-a-real-block"}, {"block": "spacer"}]}
    templates, warnings = normalize_templates(raw)

    assert [node["block"] for node in templates["HomePage"]] == ["spacer"]
    assert any("not-a-real-block" in warning for warning in warnings)


def test_unsafe_prop_values_are_dropped():
    """prop 值含 `;` `{}` `/*` `<>` 等片段时丢弃（它们能提前闭合声明块或标签）"""
    raw = {
        "HomePage": [
            {
                "block": "html",
                "props": {
                    "content": "正常文案",
                    "semicolon": "a;b",
                    "braces": "{x}",
                    "angle": "<script>",
                    "comment": "/*no*/",
                },
            }
        ]
    }
    templates, _ = normalize_templates(raw)

    assert templates["HomePage"][0]["props"] == {"content": "正常文案"}


def test_nesting_beyond_max_depth_is_truncated():
    """超过 MAX_DEPTH 的嵌套被截断，并给出告警"""
    node: dict = {"block": "spacer"}
    for _ in range(MAX_DEPTH + 3):
        node = {"block": "section", "children": [node]}

    _, warnings = normalize_templates({"HomePage": [node]})

    assert any("嵌套超过" in warning for warning in warnings)


def test_dirty_input_is_safe():
    """脏输入不抛异常 —— 主题写错不该让整个站点 500"""
    assert normalize_templates(None) == ({}, [])
    assert normalize_templates("nope") == ({}, [])
    assert normalize_templates({"HomePage": []}) == ({}, [])
    assert normalize_templates({"HomePage": [123, None]}) == ({}, [])
    # 有内容的页面才会出现在结果里，空页面被丢弃（调用方据此回退内置页）
    assert normalize_templates({"HomePage": [], "ArchivePage": [{"block": "spacer"}]})[0].keys() == {
        "ArchivePage"
    }


def test_allowed_blocks_cover_sidebar_capability():
    """WP 侧栏能力对应的区块**必须在白名单里**（前后端契约，改了要同步前端 registry）"""
    for name in ("sidebar", "widget-categories", "widget-tags", "widget-recent"):
        assert name in ALLOWED_BLOCKS, f"{name} 必须在前端可渲染的区块白名单内"


def test_class_hook_is_length_limited_and_sanitized():
    """`class` 钩子同样受注入防护与长度限制（它会进 DOM 属性）"""
    raw = {
        "HomePage": [
            {"block": "spacer", "class": "ok-class"},
            {"block": "spacer", "class": "bad{color:red}"},
        ]
    }
    templates, _ = normalize_templates(raw)

    assert templates["HomePage"][0]["class"] == "ok-class"
    assert "class" not in templates["HomePage"][1]
