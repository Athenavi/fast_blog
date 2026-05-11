"""
Blog App Models
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-03-31 17:55:16
"""

# 引入自动生成的 Mixin
from apps.generated.auto_orm import *


class Article(ArticleMixin, TimestampMixin):
    """文章模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "articles"
        verbose_name = "文章模型"
        verbose_name_plural = "文章模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.title)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "excerpt": self.excerpt,
            "cover_image": self.cover_image,
            "category": self.category,
            "tags_list": self.tags_list,
            "views": self.views,
            "user": self.user,
            "likes": self.likes,
            "status": self.status,
            "hidden": self.hidden,
            "is_featured": self.is_featured,
            "is_vip_only": self.is_vip_only,
            "required_vip_level": self.required_vip_level,
            "article_ad": self.article_ad,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class ArticleContent(ArticleContentMixin, TimestampMixin):
    """文章内容模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "article_content"
        verbose_name = "文章内容模型"
        verbose_name_plural = "文章内容模型"

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "article": self.article,
            "passwd": self.passwd,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "language_code": self.language_code
        }


class ArticleI18n(ArticleI18nMixin, TimestampMixin):
    """文章国际化模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "article_i18n"
        verbose_name = "文章国际化模型"
        verbose_name_plural = "文章国际化模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.title)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "i18n_id": self.i18n_id,
            "article": self.article,
            "language_id": self.language_id,
            "title": self.title,
            "slug": self.slug,
            "content": self.content,
            "excerpt": self.excerpt,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class ArticleLike(ArticleLikeMixin, TimestampMixin):
    """文章点赞模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "article_likes"
        verbose_name = "文章点赞模型"
        verbose_name_plural = "文章点赞模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user,
            "article": self.article,
            "created_at": self.created_at
        }


class ArticleRevision(ArticleRevisionMixin, TimestampMixin):
    """文章修订历史模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "article_revisions"
        verbose_name = "文章修订历史"
        verbose_name_plural = "文章修订历史"
        ordering = ['-revision_number']

    def __str__(self):
        return f"Revision {self.revision_number} of Article {self.article_id_id}"


class Plugin(PluginMixin, TimestampMixin):
    """插件模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "plugins"
        verbose_name = "插件"
        verbose_name_plural = "插件"
        ordering = ['name']

    def __str__(self):
        return self.name


class Theme(ThemeMixin, TimestampMixin):
    """主题模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "themes"
        verbose_name = "主题"
        verbose_name_plural = "主题"
        ordering = ['name']

    def __str__(self):
        return self.name
