"""
存储模块
"""
from .s3_storage import s3_storage, LocalStorage

__all__ = ['s3_storage', 'LocalStorage']
