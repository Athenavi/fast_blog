"""
统一日志配置模块 — src 入口（兼容层）

从 shared.logging 导入，保持旧路径兼容性。
新代码应直接从 shared.logging 导入。
"""
from shared.logging import default_logger, get_logger, LoggerConfig  # noqa: F401

logger = default_logger  # 兼容旧代码的 import logger

__all__ = ['default_logger', 'get_logger', 'LoggerConfig', 'logger']
