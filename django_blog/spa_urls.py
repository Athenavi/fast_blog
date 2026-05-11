"""
SPA (Single Page Application) URL 处理
用于支持 Next.js 前端路由
"""
import os

from django.conf import settings
from django.urls import re_path
from django.views.generic import TemplateView

# Get the path to the Next.js build output
NEXT_BUILD_DIR = os.path.join(settings.BASE_DIR, 'frontend-next', 'out')


def get_index_view():
    """获取首页视图"""
    return TemplateView.as_view(
        template_name=os.path.join(NEXT_BUILD_DIR, 'index.html')
    )


# SPA URL patterns - catch all routes for frontend routing
urlpatterns = [
    # Catch-all pattern for SPA routing
    re_path(r'^(?!api|admin|static|media|_next).*$', get_index_view(), name='spa'),
]
