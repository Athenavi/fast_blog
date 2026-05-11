"""
Django Ninja 生成的路由配置
自动包含所有通过 routes.yaml 生成的路由
"""

from django.urls import path
from ninja import NinjaAPI

# 创建 Ninja API 实例
api = NinjaAPI(
    title="ZB Blog API - Django Ninja",
    version="1.0.0",
    description="博客系统 API - 使用 Django Ninja 实现"
)

urlpatterns = [
    # 所有 API 路由
    path('', api.urls),
]
