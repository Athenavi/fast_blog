"""
博客文章序列化器
"""
from rest_framework import serializers

from apps.blog.models import Article, ArticleContent


class ArticleListSerializer(serializers.ModelSerializer):
    """文章列表序列化器"""
    author = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    tags_list = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'slug', 'excerpt', 'cover_image',
            'author', 'category_id', 'category_name', 'tags_list',
            'views', 'likes', 'status', 'is_featured',
            'is_vip_only', 'required_vip_level', 'created_at', 'updated_at'
        )

    def get_author(self, obj):
        """获取作者信息"""
        return {
            'id': obj.user.id,
            'username': obj.user.username
        }

    def get_category_name(self, obj):
        """获取分类名称"""
        if obj.category:
            return obj.category.name
        return None

    def get_tags_list(self, obj):
        """获取标签列表"""
        # 尝试访问 tags_list 或 tags 字段
        tags_str = getattr(obj, 'tags_list', None) or getattr(obj, 'tags', None)
        if tags_str and isinstance(tags_str, str):
            return [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        return []


class ArticleDetailSerializer(serializers.ModelSerializer):
    """文章详情序列化器"""
    content = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    tags_list = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'slug', 'excerpt', 'content', 'cover_image',
            'author', 'category_id', 'category_name', 'tags_list',
            'views', 'likes', 'status', 'hidden', 'is_featured',
            'is_vip_only', 'required_vip_level', 'article_ad',
            'created_at', 'updated_at', 'user_id'
        )

    def get_content(self, obj):
        """获取文章内容"""
        try:
            content_obj = ArticleContent.objects.get(aid=obj.article_id)
            return content_obj.content
        except ArticleContent.DoesNotExist:
            return ""

    def get_author(self, obj):
        """获取作者信息"""
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email
        }

    def get_category_name(self, obj):
        """获取分类名称"""
        if obj.category:
            return obj.category.name
        return None

    def get_tags_list(self, obj):
        """获取标签列表"""
        # 尝试访问 tags_list 或 tags 字段
        tags_str = getattr(obj, 'tags_list', None) or getattr(obj, 'tags', None)
        if tags_str and isinstance(tags_str, str):
            return [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        return []


class ArticleCreateUpdateSerializer(serializers.ModelSerializer):
    """文章创建和更新序列化器"""
    content = serializers.CharField(write_only=True, required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        write_only=True,
        help_text="标签列表"
    )

    class Meta:
        model = Article
        fields = (
            'title', 'slug', 'excerpt', 'content', 'cover_image',
            'category_id', 'tags', 'status', 'hidden', 'is_featured',
            'is_vip_only', 'required_vip_level', 'article_ad'
        )

    def create(self, validated_data):
        """创建文章"""
        content = validated_data.pop('content', '')
        tags = validated_data.pop('tags', None)
        request = self.context.get('request')

        # 将 tags 转换为 tags_list
        if tags is not None:
            if isinstance(tags, list):
                validated_data['tags_list'] = ';'.join(tags)
            elif isinstance(tags, str):
                validated_data['tags_list'] = tags
            else:
                validated_data['tags_list'] = ''
        else:
            validated_data['tags_list'] = ''

        article = Article.objects.create(
            user=request.user,
            **validated_data
        )

        # 创建文章内容
        if content:
            ArticleContent.objects.create(
                aid=article,
                content=content
            )

        return article

    def update(self, instance, validated_data):
        """更新文章"""
        content = validated_data.pop('content', None)
        tags = validated_data.pop('tags', None)

        # 将 tags 转换为 tags_list
        if tags is not None:
            if isinstance(tags, list):
                validated_data['tags_list'] = ';'.join(tags)
            elif isinstance(tags, str):
                validated_data['tags_list'] = tags
            else:
                validated_data['tags_list'] = ''

        # 更新文章基本信息
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 更新文章内容
        if content is not None:
            ArticleContent.objects.update_or_create(
                aid=instance,
                defaults={'content': content}
            )

        return instance
