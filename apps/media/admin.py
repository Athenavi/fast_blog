"""
媒体文件管理后台配置
"""
from django.contrib import admin

from .models import Media


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    """媒体文件管理后台"""
    list_display = (
        'filename', 'user', 'file_type', 'file_size',
        'is_public', 'download_count', 'created_at'
    )
    list_filter = ('file_type', 'is_public', 'created_at')
    search_fields = ('filename', 'original_filename', 'description')
    raw_id_fields = ('user',)
    readonly_fields = (
        'file_size', 'width', 'height', 'duration',
        'download_count', 'created_at', 'updated_at'
    )
    # 暂时注释 date_hierarchy，因为 created_at 是 CharField 类型
    # date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fieldsets = (
        ('文件信息', {
            'fields': (
                'user', 'filename', 'original_filename',
                'file_path', 'file_url', 'file_type', 'mime_type'
            )
        }),
        ('媒体属性', {
            'fields': (
                'width', 'height', 'duration',
                'thumbnail_path', 'thumbnail_url'
            ),
            'classes': ('collapse',)
        }),
        ('描述信息', {
            'fields': ('description', 'alt_text')
        }),
        ('权限与统计', {
            'fields': ('is_public', 'download_count')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
