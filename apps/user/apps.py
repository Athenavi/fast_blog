"""
用户应用配置
"""
from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.user'
    verbose_name = '用户管理'

    def ready(self):
        """应用启动时的初始化操作"""
        try:
            from . import signals
        except ImportError:
            pass

        # 导入额外的模型
        try:
            from . import models_extra
            from . import models_vip
        except ImportError:
            pass
