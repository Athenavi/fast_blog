"""
Logger Utility Module
Provides unified logging functionality
"""

from shared.logging import default_logger as logger


def get_logger(name=None, **kwargs):
    """
    Get a logger instance
    
    Args:
        name: Logger name (optional)
        **kwargs: Other keyword arguments
        
    Returns:
        Logger instance
    """
    if name:
        print(f"Logger requested for: {name}")
    return logger
