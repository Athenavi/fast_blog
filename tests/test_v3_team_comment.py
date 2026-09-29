"""_pending_test_team_comment.py —— 待迁入 ``tests/`` 的**纯函数**单测

本任务的环境**禁止写 ``tests/`` 目录、禁止执行 shell**，因此把 ``content/team_comment`` 模块的
纯函数单测临时放在模块目录内（文件名以下划线开头，不会被当作业务模块导入）。恢复后应移动到
``tests/test_v3_team_comment.py``。

只覆盖**不依赖 DB / 网络 / FastAPI / 时钟**的纯函数：:

  - ``parse_mentions``  ``team_comments.mentions``（JSON 字符串）→ 整数列表
  - ``dump_mentions``   整数列表 → ``mentions`` 列字符串（去重 / 升序 / 裁剪）
  - ``build_threads``   扁平行 → 按 ``parent_id`` 组装的线程树
  - ``summarize``       评论统计（总数 / 已解决 / 未解决 / 各作者计数）

运行（在仓库根目录，确保可 ``import src.*``）::

    python -m pytest src/api/v3/modules/content/team_comment/_pending_test_team_comment.py -q

**本文件尚未运行**：本任务执行环境不允许跑 pytest，故仅静态编写；断言逐行对照
``service.py`` 的实现写出。
"""

import json

from src.api.v3.modules.content.team_comment.schema import MENTIONS_MAX_LENGTH
from src.api.v3.modules.content.team_comment.service import (
    build_threads,
    dump_mentions,
    parse_mentions,
    summarize,
)


# --------------------------------------------------------------------- parse_mentions
def test_parse_mentions_empty_and_bad_input():
    assert parse_mentions(None) == []
    assert parse_mentions("") == []
    assert parse_mentions("not json") == []
    assert parse_mentions('{"a": 1}') == []  # 非数组
    assert parse_mentions("123") == []  # 裸数字不是数组


def test_parse_mentions_ints_and_order_preserved():
    assert parse_mentions("[1, 2, 3]") == [1, 2, 3]
    assert parse_mentions("[7]") == [7]
    # 数字字符串也被接受
    assert parse_mentions('["1", 2]') == [1, 2]


def test_parse_mentions_skips_bool_and_non_int():
    # True 是 int 子类，必须被排除，不能当成 1
    assert parse_mentions("[1, true, 2]") == [1, 2]
    assert parse_mentions("[1, null, 2]") == [1, 2]
    assert parse_mentions('[1, {"x": 2}]') == [1]


# --------------------------------------------------------------------- dump_mentions
def test_dump_mentions_empty_is_none():
    assert dump_mentions(None) is None
    assert dump_mentions([]) is None
    assert dump_mentions([0]) is None
    assert dump_mentions([0, -1]) is None


def test_dump_mentions_dedup_and_sort():
    assert dump_mentions([3, 1, 2]) == "[1, 2, 3]"
    assert dump_mentions([2, 2, 1]) == "[1, 2]"
    # 只保留正整数，且过滤 bool / 非 int
    assert dump_mentions([0, -1, 2]) == "[2]"
    assert dump_mentions([True, 2]) == "[2]"
    assert dump_mentions([1, "2"]) == "[1]"


def test_dump_mentions_roundtrip():
    assert parse_mentions(dump_mentions([5, 4, 4])) == [4, 5]


def test_dump_mentions_truncates_to_column_width():
    value = dump_mentions(list(range(1, 500)))
    assert value is not None
    assert len(value) <= MENTIONS_MAX_LENGTH
    parsed = json.loads(value)
    assert parsed == sorted(parsed)  # 升序
    assert parsed[0] == 1  # 从最小的开始保留


# --------------------------------------------------------------------- build_threads
def test_build_threads_empty():
    assert build_threads([]) == []


def test_build_threads_single_root():
    rows = [{"id": 1, "parent_id": None, "created_at": None}]
    tree = build_threads(rows)
    assert len(tree) == 1
    assert tree[0]["id"] == 1
    assert tree[0]["children"] == []


def test_build_threads_nested():
    rows = [
        {"id": 1, "parent_id": None, "created_at": None},
        {"id": 2, "parent_id": 1, "created_at": None},
        {"id": 3, "parent_id": 2, "created_at": None},
    ]
    tree = build_threads(rows)
    assert [node["id"] for node in tree] == [1]
    assert [node["id"] for node in tree[0]["children"]] == [2]
    assert [node["id"] for node in tree[0]["children"][0]["children"]] == [3]


def test_build_threads_children_sorted_by_id_when_no_time():
    rows = [
        {"id": 1, "parent_id": None, "created_at": None},
        {"id": 3, "parent_id": 1, "created_at": None},
        {"id": 2, "parent_id": 1, "created_at": None},
    ]
    tree = build_threads(rows)
    assert [node["id"] for node in tree[0]["children"]] == [2, 3]


def test_build_threads_orphan_promoted_to_root():
    # 父节点不在本批数据里 → 提升为顶层，不丢评论
    rows = [
        {"id": 1, "parent_id": None, "created_at": None},
        {"id": 5, "parent_id": 99, "created_at": None},
    ]
    tree = build_threads(rows)
    assert sorted(node["id"] for node in tree) == [1, 5]


def test_build_threads_does_not_mutate_input():
    rows = [{"id": 1, "parent_id": None, "created_at": None}]
    build_threads(rows)
    assert "children" not in rows[0]  # 原行未被写坏


# --------------------------------------------------------------------- summarize
def test_summarize_empty():
    assert summarize([]) == {
        "total_comments": 0,
        "resolved_comments": 0,
        "unresolved_comments": 0,
        "by_author": [],
    }


def test_summarize_counts_and_grouping():
    rows = [
        {"author_id": 1, "is_resolved": True},
        {"author_id": 1, "is_resolved": False},
        {"author_id": 2, "is_resolved": False},
    ]
    result = summarize(rows)
    assert result["total_comments"] == 3
    assert result["resolved_comments"] == 1
    assert result["unresolved_comments"] == 2
    # 计数降序：author 1 有 2 条在前
    assert result["by_author"] == [
        {"author_id": 1, "count": 2},
        {"author_id": 2, "count": 1},
    ]


def test_summarize_tiebreak_by_author_id_asc():
    rows = [
        {"author_id": 2, "is_resolved": False},
        {"author_id": 1, "is_resolved": False},
    ]
    result = summarize(rows)
    assert result["by_author"] == [
        {"author_id": 1, "count": 1},
        {"author_id": 2, "count": 1},
    ]


def test_summarize_skips_anonymous():
    rows = [
        {"author_id": None, "is_resolved": False},
        {"author_id": 1, "is_resolved": False},
    ]
    result = summarize(rows)
    assert result["total_comments"] == 2
    assert result["by_author"] == [{"author_id": 1, "count": 1}]
