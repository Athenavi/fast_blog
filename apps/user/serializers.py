"""
用户认证序列化器
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    avatar = serializers.SerializerMethodField()
    is_vip = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'avatar', 'profile_picture',
            'bio', 'vip_level', 'is_vip', 'vip_expires_at',
            'is_active', 'is_superuser', 'date_joined', 'last_login_at'
        )
        read_only_fields = (
            'id', 'is_vip', 'vip_expires_at', 'is_active',
            'is_superuser', 'date_joined', 'last_login_at'
        )

    def get_avatar(self, obj):
        """获取头像 URL"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(
                    f'/static/avatar/{obj.profile_picture}.webp'
                )
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """用户创建序列化器"""
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password_confirm'
        )

    def validate(self, attrs):
        """验证数据"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': '两次输入的密码不一致'
            })

        # 检查用户名是否已存在
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({
                'username': '该用户名已被使用'
            })

        # 检查邮箱是否已存在
        if attrs.get('email') and User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({
                'email': '该邮箱已被注册'
            })

        return attrs

    def create(self, validated_data):
        """创建用户"""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """自定义 Token 获取序列化器"""
    username_field = 'username'

    def validate(self, attrs):
        """验证并返回 token"""
        data = super().validate(attrs)

        # 添加用户信息到响应
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
        }

        return data


class PasswordChangeSerializer(serializers.Serializer):
    """密码修改序列化器"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6)
    new_password_confirm = serializers.CharField(required=True, write_only=True, min_length=6)

    def validate_old_password(self, value):
        """验证旧密码"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('当前密码不正确')
        return value

    def validate(self, attrs):
        """验证新密码一致性"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': '两次输入的新密码不一致'
            })
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """用户资料更新序列化器"""

    class Meta:
        model = User
        fields = (
            'username', 'email', 'profile_picture', 'bio',
            'locale', 'profile_private'
        )

    def validate_username(self, value):
        """验证用户名"""
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError('该用户名已被使用')
        return value

    def validate_email(self, value):
        """验证邮箱"""
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError('该邮箱已被使用')
        return value
