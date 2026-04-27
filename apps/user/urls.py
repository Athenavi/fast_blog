"""
用户认证 URL 配置
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView, LoginView, LogoutView,
    UserProfileView, PasswordChangeView, CurrentUserView
)

urlpatterns = [
    # 认证相关
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # 用户资料
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),
]
