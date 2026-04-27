"""
博客文章 URL 配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ArticleViewSet, ArticleBySlugView, ArticleLikeView

router = DefaultRouter()
router.register(r'', ArticleViewSet, basename='article')

urlpatterns = [
    # ViewSet 路由
    path('', include(router.urls)),

    # 通过 slug 获取文章
    path('p/<slug:slug>/', ArticleBySlugView.as_view(), name='article-by-slug'),

    # 点赞文章
    path('<int:pk>/like/', ArticleLikeView.as_view(), name='article-like'),
]
