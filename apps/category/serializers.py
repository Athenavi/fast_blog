"""
分类序列化器
"""
from rest_framework import serializers

from apps.category.models import Category, CategorySubscription


class CategorySerializer(serializers.ModelSerializer):
    """分类序列化器"""
    articles_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            'id', 'name', 'slug', 'description', 'parent_id',
            'sort_order', 'icon', 'color', 'is_visible',
            'articles_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_articles_count(self, obj):
        """获取分类下的文章数量"""
        return obj.articles.filter(status=1).count() if hasattr(obj, 'articles') else 0


class CategorySubscriptionSerializer(serializers.ModelSerializer):
    """分类订阅序列化器"""
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = CategorySubscription
        fields = ('id', 'category', 'category_name', 'created_at')
        read_only_fields = ('created_at',)
