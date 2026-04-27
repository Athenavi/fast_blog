"""
用户认证视图
"""
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django_blog.exceptions import api_response
from .serializers import (
    UserSerializer, UserCreateSerializer,
    CustomTokenObtainPairSerializer,
    PasswordChangeSerializer, ProfileUpdateSerializer
)

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """用户注册视图"""
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        """重写创建方法"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            api_response(
                success=True,
                data={
                    'user': UserSerializer(user).data,
                    'message': '注册成功'
                }
            ),
            status=status.HTTP_201_CREATED
        )


class LoginView(TokenObtainPairView):
    """用户登录视图"""
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """重写 post 方法以统一响应格式"""
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # 更新最后登录时间
            user = User.objects.get(username=request.data.get('username'))
            user.last_login_at = timezone.now()
            user.last_login_ip = self.get_client_ip(request)
            user.save(update_fields=['last_login_at', 'last_login_ip'])

            response.data = api_response(
                success=True,
                data=response.data
            )

        return response

    def get_client_ip(self, request):
        """获取客户端 IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(APIView):
    """用户登出视图"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """登出操作 - 将 token 加入黑名单"""
        try:
            from datetime import datetime
            from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
            from src.utils.token_blacklist import token_blacklist
            
            # 获取 access token
            access_token = request.session.get('access_token')
            refresh_token = request.session.get('refresh_token')
            
            # 如果没有从 session 获取到，尝试从 cookie 获取
            if not access_token:
                access_token = request.COOKIES.get('access_token')
            if not refresh_token:
                refresh_token = request.COOKIES.get('refresh_token')
            
            # 将 access token 加入黑名单
            if access_token:
                try:
                    token = AccessToken(access_token)
                    exp_timestamp = token.payload.get('exp')
                    if exp_timestamp:
                        expires_at = datetime.fromtimestamp(exp_timestamp)
                        token_blacklist.add_to_blacklist(access_token, expires_at)
                except Exception as e:
                    import logging
                    logging.debug(f"无法将 access token 加入黑名单：{e}")
            
            # 将 refresh token 也加入黑名单
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    exp_timestamp = token.payload.get('exp')
                    if exp_timestamp:
                        expires_at = datetime.fromtimestamp(exp_timestamp)
                        token_blacklist.add_to_blacklist(refresh_token, expires_at)
                except Exception as e:
                    import logging
                    logging.debug(f"无法将 refresh token 加入黑名单：{e}")
            
            return Response(
                api_response(
                    success=True,
                    data={'message': '登出成功'}
                )
            )
        except Exception as e:
            import logging
            logging.error(f"Error in logout: {str(e)}")
            return Response(
                api_response(
                    success=False,
                    error='登出失败，请稍后重试'
                ),
                status=500
            )


class TokenRefreshView(TokenRefreshView):
    """刷新 Token 视图"""
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """刷新 access token"""
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            response.data = api_response(
                success=True,
                data=response.data
            )

        return response


class UserProfileView(generics.RetrieveUpdateAPIView):
    """获取和更新用户资料"""
    serializer_class = ProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """获取当前用户对象"""
        return self.request.user

    def get_serializer_context(self):
        """添加 context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """获取用户资料"""
        instance = self.get_object()
        serializer = UserSerializer(instance, context={'request': request})
        return Response(
            api_response(
                success=True,
                data=serializer.data
            )
        )

    def update(self, request, *args, **kwargs):
        """更新用户资料"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            api_response(
                success=True,
                data=UserSerializer(instance, context={'request': request}).data,
                message='资料更新成功'
            )
        )


class PasswordChangeView(APIView):
    """修改密码视图"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    def post(self, request, *args, **kwargs):
        """修改密码"""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            return Response(
                api_response(
                    success=True,
                    data={'message': '密码修改成功'}
                )
            )

        return Response(
            api_response(
                success=False,
                error=serializer.errors
            ),
            status=status.HTTP_400_BAD_REQUEST
        )


class CurrentUserView(APIView):
    """获取当前用户信息"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """获取当前用户详细信息"""
        user = request.user
        serializer = UserSerializer(user, context={'request': request})

        return Response(
            api_response(
                success=True,
                data=serializer.data
            )
        )
