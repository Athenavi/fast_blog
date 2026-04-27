"""
User App Models
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-03-31 18:05:03
"""

# 引入自动生成的 Mixin
from apps.generated.auto_orm import *
from apps.generated.auto_orm import get_table_name


class UserManager(models.Manager):
    """
    自定义 User 管理器，提供 Django 认证系统所需的方法
    """

    def get_by_natural_key(self, username):
        """
        通过自然键（用户名）获取用户
        """
        return self.get(username=username)


class CustomField(CustomFieldMixin, TimestampMixin):
    """自定义字段模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "custom_fields"
        verbose_name = "自定义字段模型"
        verbose_name_plural = "自定义字段模型"

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user,
            "field_name": self.field_name,
            "field_value": self.field_value
        }


class EmailSubscription(EmailSubscriptionMixin, TimestampMixin):
    """邮件订阅模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "email_subscriptions"
        verbose_name = "邮件订阅模型"
        verbose_name_plural = "邮件订阅模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user,
            "subscribed": self.subscribed,
            "created_at": self.created_at
        }


class Notification(NotificationMixin, TimestampMixin):
    """通知模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "notifications"
        verbose_name = "通知模型"
        verbose_name_plural = "通知模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.title)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "recipient": self.recipient,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "read_at": self.read_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class PageView(PageViewMixin, TimestampMixin):
    """页面浏览模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "page_views"
        verbose_name = "页面浏览模型"
        verbose_name_plural = "页面浏览模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user,
            "session_id": self.session_id,
            "page_url": self.page_url,
            "page_title": self.page_title,
            "referrer": self.referrer,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "device_type": self.device_type,
            "browser": self.browser,
            "platform": self.platform,
            "country": self.country,
            "city": self.city,
            "created_at": self.created_at
        }


class SearchHistory(SearchHistoryMixin, TimestampMixin):
    """搜索历史模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "search_history"
        verbose_name = "搜索历史模型"
        verbose_name_plural = "搜索历史模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user,
            "keyword": self.keyword,
            "results_count": self.results_count,
            "created_at": self.created_at
        }


class User(UserMixin):
    """用户模型（继承自动生成的 Mixin）"""

    # Django 认证系统必需的属性
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    # 认证属性
    is_anonymous = False
    is_authenticated = True

    # 设置对象管理器
    objects = UserManager()

    class Meta:
        db_table = get_table_name("users")
        verbose_name = "用户模型"
        verbose_name_plural = "用户模型"

    def __str__(self):
        return self.username

    def get_username(self):
        """获取用户名"""
        return self.username

    def set_password(self, raw_password):
        """
        设置密码（使用 Django 的密码哈希）
        """
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
        self.save(update_fields=['password'])

    def check_password(self, raw_password):
        """
        验证密码
        """
        from django.contrib.auth.hashers import check_password
        if not self.password:
            return False
        return check_password(raw_password, self.password)

    def has_perm(self, perm, obj=None):
        """
        检查用户是否有指定权限
        """
        # 简单实现：超级管理员拥有所有权限
        if self.is_superuser:
            return True
        return False

    def has_module_perms(self, module_label):
        """
        检查用户是否有访问指定应用模块的权限
        """
        # 简单实现：超级管理员拥有所有模块权限，staff 用户可以访问 admin
        if self.is_superuser or self.is_staff:
            return True
        return False

    def is_vip(self):
        """判断是否为 VIP 用户"""
        if not self.vip_level:
            return False
        # 检查 VIP 是否过期
        if self.vip_expires_at:
            from datetime import datetime
            try:
                # 如果 vip_expires_at 是字符串，尝试解析
                if isinstance(self.vip_expires_at, str):
                    expires = datetime.fromisoformat(self.vip_expires_at.replace('Z', '+00:00'))
                    return datetime.now(expires.tzinfo) < expires
                else:
                    # 如果是 datetime 对象
                    return datetime.now(self.vip_expires_at.tzinfo) < self.vip_expires_at
            except Exception:
                # 如果解析失败，只检查 vip_level
                return self.vip_level > 0
        return self.vip_level > 0

    def to_dict(self, exclude_sensitive=True):
        """转换为字典格式
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "profile_picture": self.profile_picture,
            "bio": self.bio,
            "profile_private": self.profile_private,
            "vip_level": self.vip_level,
            "vip_expires_at": self.vip_expires_at,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "date_joined": self.date_joined,
            "last_login_at": self.last_login_at,
            "locale": self.locale,
            "is_staff": self.is_staff,
            "is_2fa_enabled": self.is_2fa_enabled,
        }
        
        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
                "last_login_ip": self.last_login_ip,
                "register_ip": self.register_ip,
                "totp_secret": self.totp_secret,
                "backup_codes": self.backup_codes
            }
            data.update(sensitive_data)
        
        return data


class UserActivity(UserActivityMixin, TimestampMixin):
    """用户活动模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "user_activities"
        verbose_name = "用户活动模型"
        verbose_name_plural = "用户活动模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user,
            "activity_type": self.activity_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at
        }


class VIPFeature(VIPFeatureMixin, TimestampMixin):
    """VIP 功能特权模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "vip_features"
        verbose_name = "VIP 功能特权模型"
        verbose_name_plural = "VIP 功能特权模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.name)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "required_level": self.required_level,
            "is_active": self.is_active,
            "created_at": self.created_at
        }


class VIPPlan(VIPPlanMixin, TimestampMixin):
    """VIP 套餐模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "vip_plans"
        verbose_name = "VIP 套餐模型"
        verbose_name_plural = "VIP 套餐模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.name)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "original_price": self.original_price,
            "duration_days": self.duration_days,
            "level": self.level,
            "features": self.features,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class VIPSubscription(VIPSubscriptionMixin, TimestampMixin):
    """VIP 订阅模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "vip_subscriptions"
        verbose_name = "VIP 订阅模型"
        verbose_name_plural = "VIP 订阅模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user,
            "plan": self.plan,
            "starts_at": self.starts_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "payment_amount": self.payment_amount,
            "transaction_id": self.transaction_id,
            "created_at": self.created_at
        }
