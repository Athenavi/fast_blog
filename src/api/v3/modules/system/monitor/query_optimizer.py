"""查询优化面板：真实采集数据 + 真实计划分析

两个能力，都不引入假数据：

  - **analysis**：读 ``slow_query_logger``（由 ``src/utils/database/slow_query_hook.py``
    在引擎 ``after_cursor_execute`` 事件上**真实采集**）的数据，输出按 SQL 指纹聚合的
    "次数 × 累计耗时"排行、疑似 N+1 指纹与规则化建议。单条不慢但高频的查询只有在
    指纹维度才看得见 —— 这正是 N+1 的证据来源。
  - **explain**：对**指定的单条 SELECT** 真跑 ``EXPLAIN (FORMAT JSON)`` 并解析计划，
    指出全表扫描 / 磁盘排序 / 嵌套循环内层全扫等结构性开销所在。

安全边界（``explain``）：

  - 只接受单条 ``SELECT`` / ``WITH`` 语句：去除注释后必须以 ``select`` / ``with`` 开头、
    不含分号、不含破坏性 / 非只读关键字、长度 ≤ :data:`MAX_SQL_LENGTH`
  - 只跑 ``EXPLAIN (FORMAT JSON)``（**不带 ANALYZE**），因此目标语句永远不会被真正执行
"""

import json
import re
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.performance.slow_query_logger import slow_query_logger
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger

logger = get_logger("monitor.query_optimizer")

#: EXPLAIN 允许的最大 SQL 长度
MAX_SQL_LENGTH = 8000

#: 破坏性 / 非只读关键字（白名单之外一律拒绝）
_FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "grant", "revoke", "copy", "vacuum", "analyze", "reindex", "cluster",
    "call", "do", "set", "reset", "begin", "commit", "rollback", "lock",
    "refresh", "discard", "listen", "notify", "prepare", "deallocate", "execute",
)


def _strip_sql_comments(sql: str) -> str:
    """去掉 ``--`` 行注释与 ``/* */`` 块注释（避免用注释绕过关键字检查）"""
    without_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", without_block)


def assert_explainable_select(sql: str) -> str:
    """校验 SQL 可以安全 EXPLAIN，返回清理后的语句；不合法抛 ``BadRequestError``"""
    if not sql or not sql.strip():
        raise BadRequestError("SQL 不能为空")
    if len(sql) > MAX_SQL_LENGTH:
        raise BadRequestError(f"SQL 过长（上限 {MAX_SQL_LENGTH} 字符）")

    cleaned = _strip_sql_comments(sql).strip()
    body = cleaned.rstrip(";").rstrip()
    if ";" in body:
        raise BadRequestError("只允许单条语句")
    if not body:
        raise BadRequestError("SQL 不能为空")

    lowered = body.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise BadRequestError("只允许对 SELECT / WITH 查询做 EXPLAIN")
    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise BadRequestError(f"SQL 含不允许的关键字：{keyword.upper()}")
    return body


def _as_plan_object(plan: Any) -> Any:
    """``EXPLAIN (FORMAT JSON)`` 的返回在不同驱动下是 str / list / dict"""
    if isinstance(plan, (str, bytes, bytearray)):
        try:
            return json.loads(plan)
        except (ValueError, TypeError):
            return None
    return plan


def _iter_plan_nodes(plan: Any) -> List[Dict[str, Any]]:
    """递归展开计划树（``Plan`` / ``Plans``），返回全部节点"""
    root = plan
    if isinstance(root, list) and root:
        root = root[0]
    if isinstance(root, dict) and "Plan" in root:
        root = root["Plan"]

    nodes: List[Dict[str, Any]] = []
    stack: List[Any] = [root] if isinstance(root, dict) else []
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        nodes.append(node)
        stack.extend(node.get("Plans") or [])
    return nodes


def analyze_explain_plan(plan: Any) -> Dict[str, Any]:
    """解析 ``EXPLAIN (FORMAT JSON)`` 计划为结构化发现 + 建议"""
    nodes = _iter_plan_nodes(plan)
    if not nodes:
        return {
            "parsed": False,
            "node_types": {},
            "uses_sequential_scan": False,
            "sequential_scan_tables": [],
            "bottlenecks": [],
            "recommendations": ["未能解析查询计划：返回值不是 PostgreSQL 的 JSON 计划"],
        }

    node_types: Dict[str, int] = {}
    seq_scan_tables: List[str] = []
    for node in nodes:
        node_type = str(node.get("Node Type") or "Unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1
        if node_type == "Seq Scan":
            table = node.get("Relation Name") or node.get("Alias") or "unknown"
            if str(table) not in seq_scan_tables:
                seq_scan_tables.append(str(table))

    bottlenecks = sorted(
        (
            {
                "node_type": str(node.get("Node Type") or "Unknown"),
                "relation": node.get("Relation Name"),
                "total_cost": node.get("Total Cost"),
                "plan_rows": node.get("Plan Rows"),
                "actual_time_ms": node.get("Actual Total Time"),
            }
            for node in nodes
            if node.get("Total Cost") is not None
        ),
        key=lambda item: float(item["total_cost"] or 0),
        reverse=True,
    )[:3]

    recommendations: List[str] = []
    if seq_scan_tables:
        recommendations.append(
            "存在全表扫描（Seq Scan）：" + "、".join(seq_scan_tables)
            + " —— 若这些表的过滤列选择度高，考虑给过滤列 / 连接列建索引"
        )
    if any(node.get("Node Type") == "Nested Loop" for node in nodes) and seq_scan_tables:
        recommendations.append("嵌套循环（Nested Loop）内层出现全表扫描：优先给内层连接列建索引")
    disk_sorts = [
        node
        for node in nodes
        if str(node.get("Node Type", "")).startswith("Sort")
           and "disk" in str(node.get("Sort Method") or "").lower()
    ]
    if disk_sorts:
        recommendations.append("排序落盘（Sort Method 含 disk）：提高 work_mem 或为排序列建索引")
    if not recommendations:
        recommendations.append("计划中未见全表扫描 / 磁盘排序 / 嵌套循环全扫的结构性开销")

    return {
        "parsed": True,
        "node_types": node_types,
        "uses_sequential_scan": bool(seq_scan_tables),
        "sequential_scan_tables": seq_scan_tables,
        "bottlenecks": bottlenecks,
        "recommendations": recommendations,
    }


class QueryOptimizerService:
    """查询优化面板（真实采集数据 + 真实计划分析）"""

    @staticmethod
    def analysis(
        *,
        hours: int = 24,
        limit: int = 20,
        min_executions: int = 10,
        max_avg_duration: float = 0.5,
    ) -> Dict[str, Any]:
        """按指纹聚合的慢查询分析（数据源：引擎事件采集，进程内队列）"""
        return {
            "data_source": "slow_query_logger（引擎 after_cursor_execute 事件采集，进程内队列）",
            "threshold_ms": round(slow_query_logger.threshold * 1000, 2),
            "period_hours": hours,
            "statistics": slow_query_logger.get_statistics(hours=hours),
            "by_fingerprint": slow_query_logger.get_fingerprint_stats(hours=hours, limit=limit),
            "n_plus_one": slow_query_logger.detect_n_plus_one(
                hours=hours,
                min_executions=min_executions,
                max_avg_duration=max_avg_duration,
            ),
            "suggestions": slow_query_logger.get_optimization_suggestions(),
        }

    async def explain(self, db: AsyncSession, sql: str) -> Dict[str, Any]:
        """对指定 SELECT 真跑 ``EXPLAIN (FORMAT JSON)``（不执行目标语句）"""
        safe_sql = assert_explainable_select(sql)
        try:
            plan = (await db.execute(text(f"EXPLAIN (FORMAT JSON) {safe_sql}"))).scalar()
        except Exception as exc:  # noqa: BLE001 - 语法/表不存在等应回给调用方而不是 500
            logger.warning("EXPLAIN 执行失败：%s", exc)
            raise BadRequestError(f"EXPLAIN 执行失败：{exc}") from exc

        return {
            "sql": safe_sql,
            "executed": False,  # 明确告知：只做计划分析，未执行该语句
            "analysis": analyze_explain_plan(_as_plan_object(plan)),
        }


query_optimizer_service = QueryOptimizerService()
