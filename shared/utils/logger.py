"""
日志工具模块
提供统一的日志记录功�?
"""

from shared.logging import default_logger as logger


def get_logger(name=None, **kwargs):
    """
    获取日志记录�?
    
    Args:
        name: 日志记录器名称（可选）
        **kwargs: 其他关键字参�?
        
    Returns:
        日志记录器实�?
    """
    if name:
        print(f"Logger requested for: {name}")
    return logger
