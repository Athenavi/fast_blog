"""
博客文章管理后台配置
"""
from django.contrib import admin

from .models import Article, ArticleContent, ArticleI18n, ArticleLike


class ArticleContentInline(admin.StackedInline):
    """文章内容内联"""
    model = ArticleContent
    can_delete = False
    verbose_name_plural = '文章内容'
    fields = ('content', 'passwd', 'language_code', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """文章管理后台"""
    list_display = (
        'title', 'slug', 'user', 'category', 'status',
        'views', 'likes', 'is_featured', 'is_vip_only',
        'created_at', 'updated_at'
    )
    list_filter = (
        'status', 'is_featured', 'is_vip_only', 'hidden',
        'category', 'created_at'
    )
    search_fields = ('title', 'slug', 'excerpt', 'tags')
    prepopulated_fields = {'slug': ('title',)}
    # raw_id_fields = ('user', 'category')  # 注释掉，因为使用的是 SQLAlchemy 模型
    readonly_fields = ('views', 'likes', 'created_at', 'updated_at')
    # 暂时注释 date_hierarchy，因为 created_at 是 CharField 类型
    # date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fieldsets = (
        ('基本信息', {
            'fields': (
                'title', 'slug', 'user', 'category',
                'excerpt', 'tags', 'cover_image'
            )
        }),
        ('状态设置', {
            'fields': (
                'status', 'hidden', 'is_featured',
                'is_vip_only', 'required_vip_level'
            )
        }),
        ('统计信息', {
            'fields': ('views', 'likes', 'article_ad'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # 暂时禁用内联，解决外键引用问题
    # inlines = [ArticleContentInline]

    def save_model(self, request, obj, form, change):
        """保存模型时自动更新 slug"""
        if not change and not obj.slug:
            # 如果是新建且没有 slug，自动生成
            from django.utils.text import slugify
            obj.slug = slugify(obj.title, allow_unicode=True) or str(obj.id)
        super().save_model(request, obj, form, change)


@admin.register(ArticleContent)
class ArticleContentAdmin(admin.ModelAdmin):
    """文章内容管理"""
    list_display = ('id', 'language_code', 'updated_at')
    list_filter = ('language_code',)
    search_fields = ('content',)
    readonly_fields = ('updated_at',)


@admin.register(ArticleI18n)
class ArticleI18nAdmin(admin.ModelAdmin):
    """文章多语言管理"""
    list_display = ('article', 'language_id', 'title', 'created_at')
    list_filter = ('language_id',)
    search_fields = ('title', 'content')
    # raw_id_fields = ('article',)  # 注释掉，因为使用的是 SQLAlchemy 模型
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ArticleLike)
class ArticleLikeAdmin(admin.ModelAdmin):
    """文章点赞管理"""
    list_display = ('id', 'user', 'article', 'created_at')
    list_filter = ('created_at',)
    # raw_id_fields = ('user', 'article')  # 注释掉，因为使用的是 SQLAlchemy 模型
    readonly_fields = ('created_at',)
