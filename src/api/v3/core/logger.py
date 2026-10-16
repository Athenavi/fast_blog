"""V3 统一 logger

结构对齐 FastApiAdmin `app/core/logger.py`。项目已在 ``src/app.py`` 完成 logging 配置，
这里只做命名空间收敛，保证 v3 日志可与 v2（``fastblog.api``）区分开。
"""

import logging

_PREFIX = "fastblog.api.v3"


def get_logger(name: str | None = None) -> logging.Logger:
    """取 v3 命名空间下的 logger，例如 ``get_logger("discover")``"""
    return logging.getLogger(f"{_PREFIX}.{name}" if name else _PREFIX)
