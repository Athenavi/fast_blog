"""
用户认证视图 - 使用 Django 模板渲染
"""
import logging
import os

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from rest_framework_simplejwt.tokens import RefreshToken

from apps.user.models import User
from src.setting import app_config

logger = logging.getLogger(__name__)


@csrf_protect
def login_view(request):
    """登录页面视图"""
    if request.user.is_authenticated:
        return redirect('/profile')

    error_message = None
    success_message = None

    # 从 URL 参数获取成功消息
    if request.GET.get('registered'):
        success_message = '注册成功，请登录'

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        if not username or not password:
            error_message = '用户名和密码不能为空'
        else:
            user = authenticate(request, username=username, password=password)

            if user is None:
                error_message = '用户名或密码错误'
            elif not user.is_active:
                error_message = '账户已被禁用'
            else:
                # 登录成功
                login(request, backend='django.contrib.auth.backends.ModelBackend')

                # 更新最后登录时间
                user.last_login_at = timezone.now()
                user.save(update_fields=['last_login_at'])

                # 生成 JWT token 并保存到 session
                refresh = RefreshToken.for_user(user)
                request.session['access_token'] = str(refresh.access_token)
                request.session['refresh_token'] = str(refresh)

                # 设置 cookie（用于前后端统一认证）
                response = redirect('/profile')
                # 根据环境自动设置 Cookie 安全标志
                is_https = str(app_config.domain).startswith('https://') or os.environ.get('DEBUG', 'False').lower() == 'false'
                response.set_cookie(
                    'access_token',
                    str(refresh.access_token),
                    max_age=3600,  # 1 小时
                    httponly=True,  # 改为 True，提高安全性
                    secure=is_https,  # 生产环境（HTTPS）设为 True
                    samesite='lax'  # 改为 lax，平衡安全性和可用性
                )

                if remember_me:
                    # 如果选择记住我，延长 session 过期时间
                    request.session.set_expiry(1209600)  # 2 周
                    response.set_cookie(
                        'refresh_token',
                        str(refresh),
                        max_age=1209600,  # 2 周
                        httponly=True,
                        secure=is_https,
                        samesite='lax'
                    )
                else:
                    request.session.set_expiry(3600)  # 1 小时

                return response

    return render(request, 'auth/login.html', {
        'error_message': error_message,
        'success_message': success_message,
        'csrf_token': request.META.get('CSRF_COOKIE')
    })


@csrf_protect
def register_view(request):
    """注册页面视图"""
    if request.user.is_authenticated:
        return redirect('/profile')

    error_message = None

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        terms = request.POST.get('terms')

        # 验证
        if not username or not email or not password:
            error_message = '用户名、邮箱和密码不能为空'
        elif len(username) < 3:
            error_message = '用户名至少需要 3 个字符'
        elif len(password) < 8:
            error_message = '密码至少需要 8 个字符'
        elif password != confirm_password:
            error_message = '两次输入的密码不一致'
        elif not terms:
            error_message = '请同意服务条款和隐私政策'
        else:
            # 检查用户名是否已存在
            if User.objects.filter(username=username).exists():
                error_message = '用户名已存在'
            # 检查邮箱是否已存在
            elif User.objects.filter(email=email).exists():
                error_message = '邮箱已被注册'
            else:
                # 创建用户
                try:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        is_active=True
                    )

                    # 自动登录
                    login(request, backend='django.contrib.auth.backends.ModelBackend')

                    # 生成 JWT token
                    refresh = RefreshToken.for_user(user)
                    request.session['access_token'] = str(refresh.access_token)
                    request.session['refresh_token'] = str(refresh)

                    # 设置 cookie
                    response = redirect('/profile')
                    # 根据环境自动设置 Cookie 安全标志
                    is_https = str(app_config.domain).startswith('https://') or os.environ.get('DEBUG', 'False').lower() == 'false'
                    response.set_cookie(
                        'access_token',
                        str(refresh.access_token),
                        max_age=3600,
                        httponly=True,
                        secure=is_https,
                        samesite='lax'
                    )
                    response.set_cookie(
                        'refresh_token',
                        str(refresh),
                        max_age=3600,
                        httponly=True,
                        secure=is_https,
                        samesite='lax'
                    )

                    return response
                except Exception as e:
                    logger.error(f"注册失败：{str(e)}")
                    error_message = f'注册失败：{str(e)}'

    return render(request, 'auth/register.html', {
        'error_message': error_message,
        'username': request.POST.get('username') if request.method == 'POST' else '',
        'email': request.POST.get('email') if request.method == 'POST' else '',
        'csrf_token': request.META.get('CSRF_COOKIE')
    })


@login_required(login_url='/login')
def logout_view(request):
    """登出视图"""
    logout(request)

    # 清除 session 中的 token
    request.session.pop('access_token', None)
    request.session.pop('refresh_token', None)

    # 清除 cookie
    response = redirect('/login')
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')

    return response
