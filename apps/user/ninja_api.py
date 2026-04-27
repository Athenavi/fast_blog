"""
用户认证相关的 Django Ninja API
兼容 FastAPI 风格
"""
from django.contrib.auth import authenticate, logout
from django.http import HttpRequest
from ninja import Router, Form
from rest_framework_simplejwt.tokens import RefreshToken

from apps.user.models import User
from django_blog.django_ninja_compat import ApiResponse

router = Router()


@router.post("/register", summary="用户注册")
def register(
        request: HttpRequest,
        username: str = Form(..., description="用户名"),
        email: str = Form(..., description="邮箱"),
        password: str = Form(..., description="密码"),
):
    """用户注册 API"""
    try:
        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            return ApiResponse(success=False, error="用户名已存在")

        # 检查邮箱是否已存在
        if User.objects.filter(email=email).exists():
            return ApiResponse(success=False, error="邮箱已被注册")

        # 创建用户
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # 生成 token
        refresh = RefreshToken.for_user(user)

        return ApiResponse(
            success=True,
            data={
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                },
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh)
            },
            message="注册成功"
        )
    except Exception as e:
        import traceback
        print(f"Error in register: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/login", summary="用户登录")
def login_api(
        request: HttpRequest,
        username: str = Form(..., description="用户名"),
        password: str = Form(..., description="密码"),
):
    """用户登录 API"""
    try:
        # 验证用户
        user = authenticate(request, username=username, password=password)

        if not user:
            return ApiResponse(success=False, error="用户名或密码错误")

        if not user.is_active:
            return ApiResponse(success=False, error="账户已被禁用")

        # 生成 JWT token
        refresh = RefreshToken.for_user(user)

        # 更新最后登录时间
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])

        return ApiResponse(
            success=True,
            data={
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "profile_picture": user.profile_picture or None
                },
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh)
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in login_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/logout", summary="用户登出")
async def logout_api(request: HttpRequest):
    """用户登出 API"""
    try:
        logout(request)
        return ApiResponse(success=True, message="登出成功")
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/profile", summary="获取用户资料")
def get_profile(request: HttpRequest):
    """获取当前登录用户的资料"""
    try:
        if not request.user.is_authenticated:
            return ApiResponse(success=False, error="未登录")

        user = request.user
        return ApiResponse(
            success=True,
            data={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "bio": user.bio or "",
                "profile_picture": user.profile_picture or None,
                "vip_level": user.vip_level or 0,
                "is_staff": user.is_staff,
                "created_at": user.date_joined.isoformat() if user.date_joined else None
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.put("/profile", summary="更新用户资料")
def update_profile(
        request: HttpRequest,
        bio: str = Form(None, description="个人简介"),
        profile_picture: str = Form(None, description="头像 URL"),
):
    """更新用户资料 API"""
    try:
        if not request.user.is_authenticated:
            return ApiResponse(success=False, error="未登录")

        user = request.user

        if bio is not None:
            user.bio = bio
        if profile_picture is not None:
            user.profile_picture = profile_picture

        user.save(update_fields=['bio', 'profile_picture'])

        return ApiResponse(
            success=True,
            data={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "bio": user.bio,
                "profile_picture": user.profile_picture
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# 导入 timezone
from django.utils import timezone
