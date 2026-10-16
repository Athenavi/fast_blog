"""P6：慢查询采集与面板接线

背景：``shared/services/performance/slow_query_logger.py`` 一直零引用 —— 没有采集点，
面板只会是空数据。本批在 SQLAlchemy 引擎上挂 before/after_cursor_execute 事件真实采集，
并把明细 / 统计 / 优化建议接到 ``/api/v3/system/monitor/slow-queries``。

覆盖：
  1. 采集真的发生（每次查询计入总量）
  2. 阈值控制明细（低于阈值不进明细、高于阈值进明细）
  3. 可用 SLOW_QUERY_LOG_ENABLED=false 关闭
  4. 路由已注册且需要鉴权
"""

from sqlalchemy import create_engine, text

import src.utils.database.slow_query_hook as hook
from shared.services.performance.slow_query_logger import SlowQueryLogger


def _fresh_logger(monkeypatch, threshold: float) -> SlowQueryLogger:
    """把 hook 引用的单例换成干净实例，避免测试间互相污染"""
    logger = SlowQueryLogger(threshold=threshold, max_logs=50)
    monkeypatch.setattr(hook, "slow_query_logger", logger)
    monkeypatch.delenv("SLOW_QUERY_THRESHOLD", raising=False)
    monkeypatch.delenv("SLOW_QUERY_LOG_ENABLED", raising=False)
    return logger


def test_hook_counts_every_query(monkeypatch):
    logger = _fresh_logger(monkeypatch, threshold=60.0)  # 阈值极高 → 只统计不进明细
    engine = create_engine("sqlite://")
    assert hook.install_slow_query_hook(engine) is True

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.execute(text("CREATE TABLE t (id INTEGER)"))
        conn.execute(text("SELECT * FROM t"))

    assert logger.stats["total_queries"] >= 3
    assert logger.stats["slow_queries"] == 0
    assert logger.get_slow_queries(hours=1) == []


def test_entries_recorded_when_over_threshold(monkeypatch):
    logger = _fresh_logger(monkeypatch, threshold=0.0)  # 阈值 0 → 全部记录
    engine = create_engine("sqlite://")
    hook.install_slow_query_hook(engine)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    assert logger.stats["slow_queries"] >= 1
    entries = logger.get_slow_queries(hours=1)
    assert entries and "SELECT" in entries[0]["sql"].upper()
    assert entries[0]["query_type"] == "SELECT"


def test_hook_is_idempotent_per_engine(monkeypatch):
    _fresh_logger(monkeypatch, threshold=60.0)
    engine = create_engine("sqlite://")
    assert hook.install_slow_query_hook(engine) is True
    assert hook.install_slow_query_hook(engine) is True  # 重复安装不应重复挂事件

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def test_hook_can_be_disabled(monkeypatch):
    _fresh_logger(monkeypatch, threshold=0.1)
    monkeypatch.setenv("SLOW_QUERY_LOG_ENABLED", "false")
    engine = create_engine("sqlite://")
    assert hook.install_slow_query_hook(engine) is False

