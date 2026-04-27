"""
博客应用配置
"""
from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.blog'
    verbose_name = '博客管理'

    def ready(self):
        """应用启动时的初始化操作"""
        try:
            from . import signals
        except ImportError:
            pass
