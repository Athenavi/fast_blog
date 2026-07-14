"""
统一日志配置模块（shared 层）

使用 secure-python-utils 的 LoggerConfig 提供全局日志管理
支持根据不同模块的重要程度创建单独的日志实例
"""
import logging
import os


def _load_logger_config():
    """加载 LoggerConfig，安全处理 secure_python_utils 包的 __init__.py 导入错误"""
    try:
        import importlib
        _mod = importlib.import_module('secure_python_utils.logger.simple')
        return _mod.LoggerConfig
    except (ImportError, AttributeError, Exception) as e:
        logging.warning(f"secure_python_utils 加载失败 ({e})，使用内置日志系统")

        class _FallbackLogger:
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

        return _FallbackLogger


LoggerConfig = _load_logger_config()
get_logger = LoggerConfig.get_logger

os.makedirs("logs", exist_ok=True)
default_logger = get_logger("logs/app.log")
