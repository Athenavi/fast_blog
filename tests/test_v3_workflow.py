"""测试：通用工作流引擎（只测纯函数与校验）

不需要数据库。覆盖 ``service.py`` 中与 DB 读写分离的逻辑：

  - ``validate_definition``：定义校验的各种非法情形（重复 id / 悬空 next / 多入口 /
    无入口 / 有环 / condition 缺分支 / config 非对象 等）
  - ``evaluate_condition``：受限条件比较（运算符、类型、缺失变量等）
  - ``can_transition`` / ``is_terminal_status``：实例状态机流转规则
  - ``NODE_TYPES`` / ``INSTANCE_STATUS`` 等常量

**不测** ``register_v3_routes`` 的路由注册（本模块尚未登记进 ``DOMAIN_MODULES``，
注册面由启动期用例统一覆盖）。真实落库（``system_settings`` 的
``workflow.definitions`` / ``workflow.instances``）走运行时验证。

注意：本文件按 ``window`` 交付约定应放到 ``tests/test_v3_workflow.py``；当前子代理
对 ``tests/`` 目录无写权限，故暂存于模块目录（文件名以 ``_tmp_`` 开头，不会被 pytest 收集）。
"""

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.system.workflow.service import (
    ALLOWED_TRANSITIONS,
    BUILTIN_ACTIONS,
    CONDITION_OPS,
    INSTANCE_STATUS,
    NODE_TYPES,
    STATUS_PENDING_APPROVAL,
    can_transition,
    evaluate_condition,
    is_terminal_status,
    validate_definition,
    validate_workflow_id,
)


def _valid_definition() -> dict:
    return {
        "name": "示例工作流",
        "description": "覆盖三类节点",
        "nodes": [
            {"id": "start", "type": "action", "config": {"action": "log", "message": "hi"}, "next": "check"},
            {
                "id": "check",
                "type": "condition",
                "config": {"expression": {"var": "count", "op": ">", "value": 10}},
                "true_next": "big",
                "false_next": "small",
            },
            {"id": "big", "type": "approval", "config": {"approver": "admin"}, "next": None},
            {"id": "small", "type": "action", "config": {"action": "set_context", "key": "x", "value": 1},
             "next": None},
        ],
    }


# ------------------------------------------------------------------ 常量
def test_enum_constants():
    assert NODE_TYPES == ("action", "condition", "approval")
    assert INSTANCE_STATUS == ("pending", "running", "completed", "failed", "cancelled")
    assert STATUS_PENDING_APPROVAL == "pending_approval"
    assert "http_request" in BUILTIN_ACTIONS
    assert set(CONDITION_OPS) == {">", ">=", "<", "<=", "==", "!="}


# ------------------------------------------------------------------ 定义校验：合法
def test_validate_definition_accepts_valid():
    normalized = validate_definition(_valid_definition())

    assert len(normalized["nodes"]) == 4
    assert normalized["name"] == "示例工作流"
    assert {node["id"] for node in normalized["nodes"]} == {"start", "check", "big", "small"}


def test_validate_definition_normalizes_node_ids():
    definition = _valid_definition()
    definition["nodes"][0]["id"] = "  start  "

    normalized = validate_definition(definition)

    assert "start" in {node["id"] for node in normalized["nodes"]}


def test_validate_definition_allows_none_branch_as_end():
    definition = {
        "nodes": [
            {
                "id": "entry",
                "type": "condition",
                "config": {"expression": {"var": "x", "op": "==", "value": 1}},
                "true_next": None,
                "false_next": None,
            },
        ]
    }

    normalized = validate_definition(definition)

    assert normalized["nodes"][0]["id"] == "entry"


def test_validate_definition_returns_fresh_nodes():
    definition = _valid_definition()
    normalized = validate_definition(definition)
    normalized["nodes"][0]["id"] = "changed"

    assert definition["nodes"][0]["id"] == "start"


# ------------------------------------------------------------------ 定义校验：非法
@pytest.mark.parametrize("bad", [None, [], "nodes", 5])
def test_validate_definition_rejects_non_dict(bad):
    with pytest.raises(BadRequestError):
        validate_definition(bad)


@pytest.mark.parametrize("nodes", [None, [], "x", {}, [1, 2]])
def test_validate_definition_rejects_bad_nodes_list(nodes):
    with pytest.raises(BadRequestError):
        validate_definition({"nodes": nodes})


def test_validate_definition_rejects_non_dict_node():
    with pytest.raises(BadRequestError):
        validate_definition({"nodes": ["not-a-node"]})


@pytest.mark.parametrize("node_id", [None, "", "   ", 5])
def test_validate_definition_rejects_bad_id(node_id):
    with pytest.raises(BadRequestError):
        validate_definition({"nodes": [{"id": node_id, "type": "action"}]})


def test_validate_definition_rejects_duplicate_id():
    definition = {
        "nodes": [
            {"id": "a", "type": "action", "next": "b"},
            {"id": "b", "type": "action", "next": None},
            {"id": "a", "type": "action", "next": None},
        ]
    }
    with pytest.raises(BadRequestError):
        validate_definition(definition)


def test_validate_definition_rejects_unknown_type():
    with pytest.raises(BadRequestError):
        validate_definition({"nodes": [{"id": "a", "type": "delay", "next": None}]})


def test_validate_definition_rejects_non_dict_config():
    with pytest.raises(BadRequestError):
        validate_definition({"nodes": [{"id": "a", "type": "action", "config": [1, 2], "next": None}]})


def test_validate_definition_rejects_dangling_next():
    with pytest.raises(BadRequestError):
        validate_definition({"nodes": [{"id": "a", "type": "action", "next": "ghost"}]})


def test_validate_definition_rejects_dangling_true_next():
    definition = {
        "nodes": [
            {"id": "a", "type": "condition", "config": {}, "true_next": "ghost", "false_next": None}
        ]
    }
    with pytest.raises(BadRequestError):
        validate_definition(definition)


@pytest.mark.parametrize("missing", ["true_next", "false_next"])
def test_validate_definition_rejects_condition_missing_branch(missing):
    node = {"id": "a", "type": "condition", "config": {}, "true_next": None, "false_next": None}
    node.pop(missing)
    with pytest.raises(BadRequestError):
        validate_definition({"nodes": [node]})


def test_validate_definition_rejects_multiple_entry_nodes():
    definition = {
        "nodes": [
            {"id": "a", "type": "action", "next": "b"},
            {"id": "b", "type": "action", "next": None},
            {"id": "c", "type": "action", "next": None},
        ]
    }
    with pytest.raises(BadRequestError):
        validate_definition(definition)


def test_validate_definition_rejects_no_entry_pure_cycle():
    definition = {
        "nodes": [
            {"id": "a", "type": "action", "next": "b"},
            {"id": "b", "type": "action", "next": "a"},
        ]
    }
    with pytest.raises(BadRequestError):
        validate_definition(definition)


def test_validate_definition_rejects_cycle_with_entry():
    definition = {
        "nodes": [
            {"id": "entry", "type": "action", "next": "a"},
            {"id": "a", "type": "action", "next": "b"},
            {"id": "b", "type": "action", "next": "a"},
        ]
    }
    with pytest.raises(BadRequestError):
        validate_definition(definition)


# ------------------------------------------------------------------ 条件求值
@pytest.mark.parametrize(
    "actual,op,expected,result",
    [
        (20, ">", 10, True),
        (5, ">", 10, False),
        (10, ">=", 10, True),
        (9, ">=", 10, False),
        (5, "<", 10, True),
        (10, "<=", 10, True),
        (11, "<=", 10, False),
        (10, "==", 10, True),
        (10, "==", 11, False),
        (10, "!=", 11, True),
        (10, "!=", 10, False),
    ],
)
def test_evaluate_condition_numeric(actual, op, expected, result):
    expression = {"var": "count", "op": op, "value": expected}

    assert evaluate_condition(expression, {"count": actual}) is result


def test_evaluate_condition_floats_and_equality_of_strings():
    assert evaluate_condition({"var": "r", "op": ">", "value": 0.5}, {"r": 0.75}) is True
    assert evaluate_condition({"var": "s", "op": "==", "value": "ok"}, {"s": "ok"}) is True
    assert evaluate_condition({"var": "s", "op": "!=", "value": "ok"}, {"s": "no"}) is True


def test_evaluate_condition_missing_var_raises():
    with pytest.raises(BadRequestError):
        evaluate_condition({"var": "missing", "op": "==", "value": 1}, {})


def test_evaluate_condition_unknown_op_raises():
    with pytest.raises(BadRequestError):
        evaluate_condition({"var": "x", "op": "~", "value": 1}, {"x": 1})


def test_evaluate_condition_type_mismatch_raises():
    with pytest.raises(BadRequestError):
        evaluate_condition({"var": "s", "op": ">", "value": 1}, {"s": "text"})


def test_evaluate_condition_bool_order_raises():
    with pytest.raises(BadRequestError):
        evaluate_condition({"var": "b", "op": ">", "value": 0}, {"b": True})


@pytest.mark.parametrize("expr", [None, [1, 2], "x"])
def test_evaluate_condition_non_dict_expression_raises(expr):
    with pytest.raises(BadRequestError):
        evaluate_condition(expr, {"x": 1})


def test_evaluate_condition_missing_var_name_raises():
    with pytest.raises(BadRequestError):
        evaluate_condition({"op": "==", "value": 1}, {"x": 1})


# ------------------------------------------------------------------ 状态机
@pytest.mark.parametrize(
    "current,target",
    [
        ("pending", "running"),
        ("pending", "cancelled"),
        ("running", "pending_approval"),
        ("running", "completed"),
        ("running", "failed"),
        ("running", "cancelled"),
        ("pending_approval", "running"),
        ("pending_approval", "completed"),
        ("pending_approval", "failed"),
        ("pending_approval", "cancelled"),
    ],
)
def test_can_transition_allowed(current, target):
    assert can_transition(current, target) is True


@pytest.mark.parametrize(
    "current,target",
    [
        ("completed", "running"),
        ("failed", "running"),
        ("cancelled", "running"),
        ("pending", "completed"),
        ("running", "pending"),
        ("unknown", "running"),
        ("running", "running"),
    ],
)
def test_can_transition_denied(current, target):
    assert can_transition(current, target) is False


def test_terminal_statuses_have_no_outgoing_transitions():
    for status in ("completed", "failed", "cancelled"):
        assert ALLOWED_TRANSITIONS[status] == frozenset()
        assert is_terminal_status(status) is True


def test_is_terminal_status_for_running_states():
    assert is_terminal_status("pending") is False
    assert is_terminal_status("running") is False
    assert is_terminal_status("pending_approval") is False


# ------------------------------------------------------------------ workflow_id
def test_validate_workflow_id_strips_and_checks():
    assert validate_workflow_id("  demo  ") == "demo"


@pytest.mark.parametrize("bad", ["", "   ", None, 5, "x" * 101])
def test_validate_workflow_id_rejects_bad(bad):
    with pytest.raises(BadRequestError):
        validate_workflow_id(bad)
