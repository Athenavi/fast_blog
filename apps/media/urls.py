"""
媒体文件 URL 配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import MediaViewSet, MediaUploadView

router = DefaultRouter()
router.register(r'', MediaViewSet, basename='media')

urlpatterns = [
    path('', include(router.urls)),
    # 简单上传接口
    path('upload/', MediaUploadView.as_view(), name='media-upload'),
]
