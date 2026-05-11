"""
媒体应用配置
"""
from django.apps import AppConfig


class MediaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.media'
    verbose_name = '媒体管理'

    def ready(self):
        """应用启动时的初始化操作"""
        try:
            from . import signals
        except ImportError:
            pass

        # 导入额外的模型
        try:
            from . import models_upload
        except ImportError:
            pass
