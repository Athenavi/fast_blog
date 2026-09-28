"""数据库慢查询采集：把每次 SQL 的执行耗时交给 ``SlowQueryLogger``。

为什么需要：``shared/services/performance/slow_query_logger.py`` 有完整的慢查询统计与
优化建议，但全项目**没有任何采集点** —— 没有采集，任何「慢查询面板」都只会是空数据。

做法：在 SQLAlchemy 引擎的 ``sync_engine`` 上挂 before/after_cursor_execute 事件：

  - **每次**查询都计入 ``total_queries`` / ``total_time``（几次整数加法，开销可忽略）
  - 只有超过阈值（默认 100ms，可用 ``SLOW_QUERY_THRESHOLD`` 秒数覆盖）的才进入明细队列
  - 采集本身出错绝不影响查询（事件回调里吞掉异常）

统计是**进程内内存队列**（默认保留最近 1000 条）。多 worker 部署下各进程独立，
如需全局视图应把明细另写 Redis 或表。

环境变量：
  - ``SLOW_QUERY_LOG_ENABLED``（默认 true）：设为 false 可完全关闭采集
  - ``SLOW_QUERY_THRESHOLD``（默认 0.1）：慢查询阈值，单位秒
"""

import os
import time
from typing import Any, Set

from sqlalchemy import event

from shared.logging import default_logger as logger
from shared.services.performance.slow_query_logger import slow_query_logger

_CONTEXT_ATTR = "_fb_query_started_at"
_INSTALLED: Set[int] = set()


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def install_slow_query_hook(engine: Any) -> bool:
    """在引擎上安装慢查询采集（幂等）。返回是否处于启用状态。"""
    if not _env_flag("SLOW_QUERY_LOG_ENABLED", True):
        logger.info("慢查询采集已关闭（SLOW_QUERY_LOG_ENABLED=false）")
        return False

    sync_engine = getattr(engine, "sync_engine", engine)
    if id(sync_engine) in _INSTALLED:
        return True

    # 仅在显式配置了环境变量时才覆盖单例默认阈值（默认 0.1 秒）
    raw_threshold = os.getenv("SLOW_QUERY_THRESHOLD")
    if raw_threshold:
        try:
            slow_query_logger.update_threshold(float(raw_threshold))
        except ValueError:
            logger.warning("SLOW_QUERY_THRESHOLD=%r 无法解析为秒数，沿用 %.2f 秒",
                           raw_threshold, slow_query_logger.threshold)

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        setattr(context, _CONTEXT_ATTR, time.perf_counter())

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        started = getattr(context, _CONTEXT_ATTR, None)
        if started is None:
            return
        try:
            slow_query_logger.log_query(statement, time.perf_counter() - started)
        except Exception:  # noqa: BLE001 - 采集失败不得影响业务查询
            logger.debug("慢查询采集失败（已忽略）", exc_info=True)

    _INSTALLED.add(id(sync_engine))
    logger.info("慢查询采集已启用（阈值 %.0f ms）", slow_query_logger.threshold * 1000)
    return True
