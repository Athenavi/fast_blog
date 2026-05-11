"""
博客文章视图
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response

from apps.blog.models import Article
from apps.blog.serializers import (
    ArticleListSerializer, ArticleDetailSerializer,
    ArticleCreateUpdateSerializer
)
from django_blog.exceptions import api_response

logger = logging.getLogger(__name__)


class ArticleViewSet(viewsets.ModelViewSet):
    """文章视图集"""
    queryset = Article.objects.select_related('user', 'category').all()
    filterset_fields = ['status', 'category_id', 'is_featured', 'is_vip_only']
    search_fields = ['title', 'excerpt', 'tags']
    ordering_fields = ['created_at', 'updated_at', 'views', 'likes']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """根据操作返回不同的序列化器"""
        if self.action == 'list':
            return ArticleListSerializer
        elif self.action == 'retrieve':
            return ArticleDetailSerializer
        return ArticleCreateUpdateSerializer

    def get_permissions(self):
        """根据操作返回不同的权限"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        """自定义查询集"""
        queryset = super().get_queryset()

        # 非管理员和非作者只能查看已发布的文章
        if not self.request.user.is_staff:
            queryset = queryset.filter(status=1)  # 1 表示已发布

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """获取文章详情"""
        instance = self.get_object()

        # 增加浏览量
        instance.increment_views()

        serializer = self.get_serializer(instance)
        return Response(
            api_response(
                success=True,
                data=serializer.data
            )
        )

    def create(self, request, *args, **kwargs):
        """创建文章"""
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            api_response(
                success=True,
                data=ArticleDetailSerializer(serializer.instance).data,
                message='文章创建成功'
            ),
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """更新文章"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            api_response(
                success=True,
                data=ArticleDetailSerializer(instance).data,
                message='文章更新成功'
            )
        )

    def destroy(self, request, *args, **kwargs):
        """删除文章"""
        instance = self.get_object()
        instance.status = -1  # 标记为已删除
        instance.save()

        return Response(
            api_response(
                success=True,
                message='文章删除成功'
            )
        )


class ArticleBySlugView(generics.RetrieveAPIView):
    """通过 slug 获取文章详情"""
    serializer_class = ArticleDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        """通过 slug 获取文章"""
        slug = self.kwargs.get('slug')
        article = get_object_or_404(Article, slug=slug)

        # 检查文章状态
        if article.status == -1:  # 已删除
            raise Exception('文章不存在')

        # 草稿文章只对作者和管理员可见
        if article.status == 0:  # 草稿
            if not self.request.user.is_authenticated:
                raise Exception('文章不存在')

            if not (self.request.user.is_staff or article.user == self.request.user):
                raise Exception('文章不存在')

        return article

    def retrieve(self, request, *args, **kwargs):
        """获取文章详情并增加浏览量"""
        instance = self.get_object()
        instance.increment_views()

        serializer = self.get_serializer(instance)
        return Response(
            api_response(
                success=True,
                data=serializer.data
            )
        )


class ArticleLikeView(generics.GenericAPIView):
    """文章点赞视图"""
    queryset = Article.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """点赞文章"""
        article = self.get_object()

        # 检查是否已经点赞过
        from apps.blog.models import ArticleLike
        already_liked = ArticleLike.objects.filter(
            user=request.user,
            article=article
        ).exists()

        if already_liked:
            return Response(
                api_response(
                    success=False,
                    error='您已经点过赞了'
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        # 创建点赞记录
        ArticleLike.objects.create(user=request.user, article=article)

        # 增加文章点赞数
        article.likes = (article.likes or 0) + 1
        article.save(update_fields=['likes'])

        return Response(
            api_response(
                success=True,
                data={'likes': article.likes},
                message='点赞成功'
            )
        )
