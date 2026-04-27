"""
此文件已废弃 - Django 版本使用内置的 migrate 命令进行数据库迁移
保留此文件仅用于向后兼容，但不执行任何操作
"""


def run_migration_with_lock(func, *args, **kwargs):
    """
    空函数 - Django 版本中不再需要此函数
    
    Django 使用 migrate 命令自动处理迁移，无需手动加锁
    """
    print("警告：FastAPI 版本的迁移锁函数已被禁用")
    print("Django 会自动处理迁移，无需手动管理")
    return func(*args, **kwargs) if func else None


def check_and_run_migrations():
    """
    空函数 - Django 版本中不再需要此函数
    """
    print("警告：FastAPI 版本的迁移检查函数已被禁用")
    print("请运行：python manage.py migrate")
    return True
