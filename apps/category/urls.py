"""
分类 URL 配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, CategorySubscriptionViewSet

router = DefaultRouter()
router.register(r'', CategoryViewSet, basename='category')

urlpatterns = [
    path('', include(router.urls)),
    # 分类订阅单独路由
    path('subscriptions/', CategorySubscriptionViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='category-subscription-list'),
    path('subscriptions/<int:pk>/', CategorySubscriptionViewSet.as_view({'delete': 'destroy'}),
         name='category-subscription-delete'),
]
