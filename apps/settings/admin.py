"""
系统设置管理后台配置
"""
from django.contrib import admin

from .models import SystemSettings, AdminSettings, MenuItems, Menus, Pages


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """系统设置管理后台"""
    list_display = (
        'setting_key', 'setting_type', 'is_public',
        'created_at', 'updated_at'
    )
    list_filter = ('setting_type', 'is_public')
    search_fields = ('setting_key', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('设置信息', {
            'fields': (
                'setting_key', 'setting_value', 'setting_type',
                'description', 'is_public'
            )
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AdminSettings)
class AdminSettingsAdmin(admin.ModelAdmin):
    """管理员设置管理后台"""
    list_display = ('user', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MenuItems)
class MenuItemsAdmin(admin.ModelAdmin):
    """菜单项管理后台"""
    list_display = (
        'title', 'menu_id', 'parent_id', 'url',
        'order_index', 'is_active', 'created_at'
    )
    list_filter = ('is_active', 'target', 'created_at')
    search_fields = ('title', 'url')
    readonly_fields = ('created_at',)
    ordering = ('order_index', 'title')

    fieldsets = (
        ('基本信息', {
            'fields': (
                'menu_id', 'parent_id', 'title',
                'url', 'target'
            )
        }),
        ('排序与状态', {
            'fields': ('order_index', 'is_active')
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Menus)
class MenusAdmin(admin.ModelAdmin):
    """菜单管理后台"""
    list_display = (
        'name', 'slug', 'is_active',
        'created_at', 'updated_at'
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('name',)

    fieldsets = (
        ('基本信息', {
            'fields': (
                'name', 'slug', 'description'
            )
        }),
        ('状态设置', {
            'fields': ('is_active',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Pages)
class PagesAdmin(admin.ModelAdmin):
    """页面管理后台"""
    list_display = (
        'title', 'slug', 'status', 'author_id',
        'order_index', 'created_at', 'updated_at'
    )
    list_filter = ('status', 'template', 'created_at')
    search_fields = ('title', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'published_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('基本信息', {
            'fields': (
                'title', 'slug', 'author_id', 'parent_id',
                'content', 'excerpt'
            )
        }),
        ('模板与状态', {
            'fields': (
                'template', 'status', 'order_index'
            )
        }),
        ('SEO 设置', {
            'fields': (
                'meta_title', 'meta_description', 'meta_keywords'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': (
                'created_at', 'updated_at', 'published_at'
            ),
            'classes': ('collapse',)
        }),
    )
