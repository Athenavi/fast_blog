"""
统一日志配置模块（shared 层）

提供全局日志管理，支持根据不同模块的重要程度创建单独的日志实例。
使用内置 logging 实现（已移除不可用的 secure-python-utils 依赖）。
"""
import logging
import os


class _BuiltinLoggerConfig:
    @staticmethod
    def get_logger(log_file: str = None, level=logging.INFO):
        logger = logging.getLogger(f"fastblog.{log_file or 'app'}")
        logger.setLevel(level)
        if not logger.handlers:
            console = logging.StreamHandler()
            console.setLevel(level)
            fmt = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console.setFormatter(fmt)
            logger.addHandler(console)
            if log_file:
                log_dir = os.path.dirname(log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)
                fh = logging.FileHandler(log_file, encoding='utf-8')
                fh.setLevel(level)
                fh.setFormatter(fmt)
                logger.addHandler(fh)
        return logger


LoggerConfig = _BuiltinLoggerConfig
get_logger = LoggerConfig.get_logger

os.makedirs("logs", exist_ok=True)
default_logger = get_logger("logs/app.log")
