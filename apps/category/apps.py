"""
分类应用配置
"""
from django.apps import AppConfig


class CategoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.category'
    verbose_name = '分类管理'

    def ready(self):
        """应用启动时的初始化操作"""
        try:
            from . import signals
        except ImportError:
            pass
