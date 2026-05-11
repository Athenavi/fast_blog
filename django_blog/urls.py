"""Django 6 博客项目 URL 配置

本项目的 Django 后台直接使用 FastAPI 的路由代码（通过适配器转换）
因此只需要维护一套路由代码（src/api/v1/*.py），即可在两个后台运行
"""
import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.static import serve

urlpatterns = [
                  # Admin
                  path('admin/', admin.site.urls),

                  # FastAPI 原始路由 - 通过适配器在 Django 中运行
                  path('', include('django_blog.fastapi_urls')),

                  # Django Ninja 生成的路由 (基于 routes.yaml，备用)
                  # path('', include('apps.urls')),

                  # SPA fallback - 将所有其他路由指向 Next.js 构建的页面
                  path('', include('django_blog.spa_urls')),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 添加 storage/objects 目录的静态文件服务（用于媒体文件和缩略图）
storage_objects_dir = os.path.join(settings.BASE_DIR, 'storage', 'objects')
if os.path.exists(storage_objects_dir):
    urlpatterns += [
        path('storage/objects/<path:path>', serve, {
            'document_root': storage_objects_dir,
        }),
    ]

# Add static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = 'ZB Django Blog 管理后台'
admin.site.site_title = 'ZB Django Blog'
admin.site.index_title = '欢迎使用 ZB Django Blog 管理系统'
