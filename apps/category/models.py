"""
Category App Models
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-03-31 17:55:16
"""

# 引入自动生成的 Mixin
from apps.generated.auto_orm import *


class Category(CategoryMixin, TimestampMixin):
    """分类模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "categories"
        verbose_name = "分类模型"
        verbose_name_plural = "分类模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.name)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "parent_id": self.parent_id,
            "sort_order": self.sort_order,
            "icon": self.icon,
            "color": self.color,
            "is_visible": self.is_visible,
            "articles_count": self.articles_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class CategorySubscription(CategorySubscriptionMixin, TimestampMixin):
    """分类订阅模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "category_subscriptions"
        verbose_name = "分类订阅模型"
        verbose_name_plural = "分类订阅模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "category": self.category,
            "subscriber": self.subscriber,
            "created_at": self.created_at
        }
