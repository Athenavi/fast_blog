"""测试：查询优化面板与性能综合报告

不需要数据库的部分：

  - ``assert_explainable_select``：白名单与注入防护（纯字符串校验）
  - ``analyze_explain_plan``：计划解析与建议（喂构造的 JSON 计划）
  - ``slow_query_logger`` 的指纹聚合与 N+1 判据（喂真实采集接口 ``log_query``，用后清空）
  - 端点注册与鉴权（TestClient，不触发真实查询）

真正需要 DB 的 ``explain`` / ``performance-report`` 走运行时验证。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.services.performance.slow_query_logger import slow_query_logger
from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.system.monitor.query_optimizer import (
    analyze_explain_plan,
    assert_explainable_select,
)

ANALYSIS_PATH = "/api/v3/system/monitor/query-optimizer/analysis"
EXPLAIN_PATH = "/api/v3/system/monitor/query-optimizer/explain"
REPORT_PATH = "/api/v3/system/monitor/performance-report"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def _paths() -> set[str]:
    return {route.path for route in _app().routes}


@pytest.fixture()
def clean_slow_queries():
    """指纹聚合依赖进程内队列：用例前后清空，避免与其他用例互相污染"""
    slow_query_logger.clear_logs()
    yield
    slow_query_logger.clear_logs()


# ------------------------------------------------------------------ SQL 白名单
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "select id, title from articles where id = 1",
        "WITH t AS (SELECT 1 AS a) SELECT * FROM t",
        "SELECT * FROM users -- 行注释应被忽略",
        "SELECT * FROM users /* 块注释 */ WHERE id = 1",
    ],
)
def test_assert_explainable_select_accepts(sql):
    assert assert_explainable_select(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "   ",
        "INSERT INTO users (username) VALUES ('x')",
        "UPDATE users SET username = 'x'",
        "DELETE FROM users",
        "DROP TABLE users",
        "TRUNCATE users",
        "CREATE INDEX i ON users (id)",
        "SELECT 1; DROP TABLE users",
        "SELECT 1; SELECT 2",
        "/* SELECT */ UPDATE users SET username = 'x'",
        "-- SELECT\nDELETE FROM users",
        "SELECT * FROM users FOR UPDATE",
    ],
)
def test_assert_explainable_select_rejects(sql):
    with pytest.raises(BadRequestError):
        assert_explainable_select(sql)


def test_assert_explainable_select_rejects_oversized():
    with pytest.raises(BadRequestError):
        assert_explainable_select("SELECT " + "x" * 9000)


def test_assert_explainable_select_strips_trailing_semicolon():
    assert assert_explainable_select("SELECT 1;") == "SELECT 1"


# ------------------------------------------------------------------ 计划解析
def _seq_scan_plan() -> list[dict]:
    return [
        {
            "Plan": {
                "Node Type": "Sort",
                "Sort Method": "external merge  Disk: 1024kB",
                "Total Cost": 120.0,
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "articles",
                        "Total Cost": 100.0,
                        "Plan Rows": 500,
                    }
                ],
            }
        }
    ]


def test_analyze_explain_plan_flags_seq_scan_and_disk_sort():
    analysis = analyze_explain_plan(_seq_scan_plan())

    assert analysis["parsed"] is True
    assert analysis["uses_sequential_scan"] is True
    assert analysis["sequential_scan_tables"] == ["articles"]
    assert analysis["node_types"]["Seq Scan"] == 1
    assert analysis["bottlenecks"][0]["node_type"] == "Sort"
    assert any("全表扫描" in item for item in analysis["recommendations"])
    assert any("disk" in item for item in analysis["recommendations"])


def test_analyze_explain_plan_without_structural_cost():
    plan = [{"Plan": {"Node Type": "Index Scan", "Relation Name": "users", "Total Cost": 1.0}}]

    analysis = analyze_explain_plan(plan)

    assert analysis["parsed"] is True
    assert analysis["uses_sequential_scan"] is False
    assert analysis["sequential_scan_tables"] == []
    assert any("未见" in item for item in analysis["recommendations"])


def test_analyze_explain_plan_unparsable():
    analysis = analyze_explain_plan(None)

    assert analysis["parsed"] is False
    assert analysis["recommendations"]


# ------------------------------------------------------------------ 指纹聚合 / N+1
def test_fingerprint_stats_groups_by_normalized_sql(clean_slow_queries):
    for _ in range(5):
        slow_query_logger.log_query("SELECT id FROM users WHERE id = 1", 0.2, table="users")
    slow_query_logger.log_query("SELECT id FROM users WHERE id = 2", 0.4, table="users")
    slow_query_logger.log_query("SELECT count(*) FROM articles", 0.9, table="articles")

    rows = slow_query_logger.get_fingerprint_stats(hours=24)

    assert len(rows) == 2  # 前两条归一到同一指纹
    top = rows[0]
    assert top["table"] == "users"
    assert top["executions"] == 6
    assert top["max_duration"] == pytest.approx(0.4)
    assert top["avg_duration"] == pytest.approx((0.2 * 5 + 0.4) / 6)


def test_detect_n_plus_one_distinguishes_slow_sql(clean_slow_queries):
    for _ in range(12):
        slow_query_logger.log_query("SELECT id FROM users WHERE id = 1", 0.15, table="users")
    # 单次就远超阈值 → 属于"慢 SQL"，不该混进 N+1
    for _ in range(12):
        slow_query_logger.log_query("SELECT * FROM articles WHERE slug = 'x'", 2.0, table="articles")

    suspects = slow_query_logger.detect_n_plus_one(
        hours=24, min_executions=10, max_avg_duration=0.5
    )

    tables = [row["table"] for row in suspects]
    assert "users" in tables
    assert "articles" not in tables


def test_detect_n_plus_one_ignores_low_frequency(clean_slow_queries):
    for _ in range(3):
        slow_query_logger.log_query("SELECT id FROM users WHERE id = 1", 0.15, table="users")

    assert slow_query_logger.detect_n_plus_one(hours=24, min_executions=10) == []


def test_log_query_infers_table_when_not_provided(clean_slow_queries):
    """采集侧（slow_query_hook）不传 table：必须从 SQL 推断，否则 by_table 与指纹表名全空"""
    slow_query_logger.log_query("SELECT count(*) FROM user_sessions WHERE user_id = 1", 0.3)

    row = slow_query_logger.get_fingerprint_stats(hours=24)[0]

    assert row["table"] == "user_sessions"


def test_log_query_prefers_explicit_table(clean_slow_queries):
    slow_query_logger.log_query("SELECT 1 FROM ignored", 0.3, table="explicit")

    assert slow_query_logger.get_fingerprint_stats(hours=24)[0]["table"] == "explicit"

# ------------------------------------------------------------------ 端点注册与鉴权
