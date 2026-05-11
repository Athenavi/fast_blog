"""
Django 博客应用配置
"""
from django.apps import AppConfig


class DjangoBlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_blog'
    verbose_name = 'ZB Django 博客系统'

    def ready(self):
        """
        应用启动时的初始化操作
        """
        # Import signals here to ensure they're registered
        try:
            from . import signals
        except ImportError:
            pass

        # Print startup info
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Django Blog application started")
