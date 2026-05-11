"""
分类管理后台配置
"""
from django.contrib import admin

from .models import Category, CategorySubscription


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """分类管理后台"""
    list_display = (
        'name', 'slug', 'parent_id', 'sort_order',
        'is_visible', 'created_at', 'updated_at'
    )
    list_filter = ('is_visible', 'parent_id', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('sort_order', 'name')

    fieldsets = (
        ('基本信息', {
            'fields': (
                'name', 'slug', 'description',
                'icon', 'color'
            )
        }),
        ('层级与排序', {
            'fields': ('parent_id', 'sort_order')
        }),
        ('显示设置', {
            'fields': ('is_visible',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CategorySubscription)
class CategorySubscriptionAdmin(admin.ModelAdmin):
    """分类订阅管理"""
    list_display = ('subscriber', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    raw_id_fields = ('subscriber', 'category')
    readonly_fields = ('created_at',)
