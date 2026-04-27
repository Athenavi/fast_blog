"""
设置应用配置
"""
from django.apps import AppConfig


class SettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.settings'
    verbose_name = '系统设置'

    def ready(self):
        """应用启动时的初始化操作"""
        try:
            from . import signals
        except ImportError:
            pass
