"""
系统设置 URL 配置
"""
from django.urls import path

from .views import SystemSettingsView, AdminSettingsView

urlpatterns = [
    path('', SystemSettingsView.as_view(), name='system-settings'),
    path('admin/', AdminSettingsView.as_view(), name='admin-settings'),
]
