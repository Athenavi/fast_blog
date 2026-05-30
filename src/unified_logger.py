"""
统一日志配置模块

使用 secure-python-utils 的 LoggerConfig 提供全局日志管理
支持根据不同模块的重要程度创建单独的日志实例

注意：由于 secure-python-utils 包的 __init__.py 存在导入错误，
我们直接导入子模块来绕过这个问题。
"""
# 直接导入子模块，避免触发包的 __init__.py 中的错误导入
from secure_python_utils.logger.simple import LoggerConfig

# 获取 logger 函数
get_logger = LoggerConfig.get_logger

# 全局默认日志实例（用于大多数模块）
default_logger = get_logger("logs/app.log")


def get_module_logger(module_name: str, log_file: str = None):
    """
    为特定模块获取日志实例
    
    Args:
        module_name: 模块名称（如 'auth', 'articles', 'security' 等）
        log_file: 可选的单独日志文件路径，如果为 None 则使用默认日志文件
        
    Returns:
        logger 实例
    """
    if log_file:
        # 为重要模块创建单独的日志文件
        return get_logger(log_file)
    else:
        # 使用默认日志文件，但带有模块标识
        return default_logger


# 为关键模块预定义日志实例
auth_logger = get_module_logger("auth", "logs/auth.log")
security_logger = get_module_logger("security", "logs/security.log")
database_logger = get_module_logger("database", "logs/database.log")
api_logger = get_module_logger("api", "logs/api.log")
performance_logger = get_module_logger("performance", "logs/performance.log")

# 导出所有日志实例
__all__ = [
    'default_logger',
    'get_module_logger',
    'auth_logger',
    'security_logger',
    'database_logger',
    'api_logger',
    'performance_logger',
]
