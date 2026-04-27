"""
用户管理后台配置
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, CustomField, EmailSubscription, Notification, PageView, SearchHistory, UserActivity, \
    VIPFeature, VIPPlan, VIPSubscription


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户管理后台"""
    list_display = (
        'username', 'email', 'is_active', 'is_staff', 'is_superuser',
        'vip_level', 'last_login_at', 'date_joined'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'vip_level',
        'is_2fa_enabled'
    )
    search_fields = ('username', 'email', 'bio')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal Info'), {
            'fields': (
                'email', 'profile_picture', 'bio',
                'vip_level', 'vip_expires_at', 'locale'
            )
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser'
            ),
        }),
        (_('Security'), {
            'fields': (
                'is_2fa_enabled', 'totp_secret', 'backup_codes'
            ),
        }),
        (_('Important dates'), {
            'fields': (
                'last_login_at', 'last_login_ip', 'register_ip',
                'date_joined'
            )
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2',
                'is_staff', 'is_superuser', 'is_active'
            ),
        }),
    )

    readonly_fields = (
        'last_login_at', 'date_joined', 'register_ip', 'last_login_ip'
    )

    # 暂时注释 date_hierarchy，因为 date_joined 是 CharField 类型
    # date_hierarchy = 'date_joined'
    # 覆盖 BaseUserAdmin 的 filter_horizontal，因为我们没有 groups 和 user_permissions 字段
    filter_horizontal = ()


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    """自定义字段管理"""
    list_display = ('user', 'field_name', 'field_value')
    list_filter = ('field_name',)
    search_fields = ('user__username', 'field_name')
    # raw_id_fields = ('user',)  # 暂时禁用，等待迁移完成


@admin.register(EmailSubscription)
class EmailSubscriptionAdmin(admin.ModelAdmin):
    """邮件订阅管理"""
    list_display = ('user', 'subscribed', 'created_at')
    list_filter = ('subscribed',)
    search_fields = ('user__username', 'user__email')
    # raw_id_fields = ('user',)  # 暂时禁用，等待迁移完成


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """通知管理后台"""
    list_display = (
        'title', 'recipient', 'type', 'is_read',
        'read_at', 'created_at'
    )
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    raw_id_fields = ('recipient',)
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('通知信息', {
            'fields': (
                'recipient', 'type', 'title',
                'message'
            )
        }),
        ('阅读状态', {
            'fields': ('is_read', 'read_at')
        }),
        ('时间信息', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    """页面浏览管理后台"""
    list_display = (
        'user', 'page_title', 'device_type',
        'browser', 'country', 'created_at'
    )
    list_filter = (
        'device_type', 'browser', 'platform',
        'country', 'created_at'
    )
    search_fields = (
        'page_url', 'page_title', 'user__username',
        'ip_address', 'city'
    )
    raw_id_fields = ('user',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    fieldsets = (
        ('用户信息', {
            'fields': (
                'user', 'session_id'
            )
        }),
        ('页面信息', {
            'fields': (
                'page_url', 'page_title', 'referrer'
            )
        }),
        ('设备与浏览器', {
            'fields': (
                'user_agent', 'device_type', 'browser',
                'platform'
            ),
            'classes': ('collapse',)
        }),
        ('地理位置', {
            'fields': (
                'ip_address', 'country', 'city'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    """搜索历史管理后台"""
    list_display = ('user', 'keyword', 'results_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('keyword', 'user__username')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    fieldsets = (
        ('搜索信息', {
            'fields': (
                'user', 'keyword', 'results_count'
            )
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """用户活动管理后台"""
    list_display = (
        'user', 'activity_type', 'target_type',
        'ip_address', 'created_at'
    )
    list_filter = ('activity_type', 'target_type', 'created_at')
    search_fields = (
        'details', 'user__username', 'ip_address'
    )
    raw_id_fields = ('user',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    fieldsets = (
        ('活动信息', {
            'fields': (
                'user', 'activity_type', 'target_type',
                'target_id', 'details'
            )
        }),
        ('请求信息', {
            'fields': (
                'ip_address', 'user_agent'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(VIPFeature)
class VIPFeatureAdmin(admin.ModelAdmin):
    """VIP 功能特权管理后台"""
    list_display = (
        'name', 'code', 'required_level',
        'is_active', 'created_at'
    )
    list_filter = ('is_active', 'required_level')
    search_fields = ('name', 'code', 'description')
    prepopulated_fields = {'code': ('name',)}
    readonly_fields = ('created_at',)
    ordering = ('required_level', 'name')

    fieldsets = (
        ('功能信息', {
            'fields': (
                'name', 'code', 'description',
                'required_level'
            )
        }),
        ('状态设置', {
            'fields': ('is_active',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(VIPPlan)
class VIPPlanAdmin(admin.ModelAdmin):
    """VIP 套餐管理后台"""
    list_display = (
        'name', 'level', 'price',
        'duration_days', 'is_active', 'created_at'
    )
    list_filter = ('is_active', 'level')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('level', 'price')

    fieldsets = (
        ('套餐信息', {
            'fields': (
                'name', 'description', 'level',
                'features'
            )
        }),
        ('价格与周期', {
            'fields': (
                'price', 'original_price', 'duration_days'
            )
        }),
        ('状态设置', {
            'fields': ('is_active',)
        }),
        ('时间信息', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(VIPSubscription)
class VIPSubscriptionAdmin(admin.ModelAdmin):
    """VIP 订阅管理后台"""
    list_display = (
        'user', 'plan', 'status',
        'starts_at', 'expires_at', 'created_at'
    )
    list_filter = ('status', 'plan', 'created_at')
    search_fields = (
        'user__username', 'user__email',
        'transaction_id'
    )
    raw_id_fields = ('user', 'plan')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    fieldsets = (
        ('订阅信息', {
            'fields': (
                'user', 'plan', 'status'
            )
        }),
        ('时间信息', {
            'fields': (
                'starts_at', 'expires_at'
            )
        }),
        ('支付信息', {
            'fields': (
                'payment_amount', 'transaction_id'
            ),
            'classes': ('collapse',)
        }),
        ('创建时间', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
