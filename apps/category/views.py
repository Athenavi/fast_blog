"""
分类视图
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from apps.category.models import Category, CategorySubscription
from apps.category.serializers import CategorySerializer, CategorySubscriptionSerializer
from django_blog.exceptions import api_response


class CategoryViewSet(viewsets.ModelViewSet):
    """分类视图集"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_visible', 'parent_id']
    search_fields = ['name', 'slug', 'description']
    ordering_fields = ['sort_order', 'name', 'created_at']
    ordering = ['sort_order', 'name']

    def get_permissions(self):
        """根据操作返回不同的权限"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def list(self, request, *args, **kwargs):
        """获取分类列表"""
        queryset = self.filter_queryset(self.get_queryset())

        # 只返回可见分类给普通用户
        if not request.user.is_staff:
            queryset = queryset.filter(is_visible=True)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            api_response(
                success=True,
                data=serializer.data
            )
        )

    def create(self, request, *args, **kwargs):
        """创建分类"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            api_response(
                success=True,
                data=serializer.data,
                message='分类创建成功'
            ),
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """更新分类"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            api_response(
                success=True,
                data=serializer.data,
                message='分类更新成功'
            )
        )

    def destroy(self, request, *args, **kwargs):
        """删除分类"""
        instance = self.get_object()
        instance.delete()

        return Response(
            api_response(
                success=True,
                message='分类删除成功'
            )
        )


class CategorySubscriptionViewSet(viewsets.ModelViewSet):
    """分类订阅视图集"""
    serializer_class = CategorySubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """获取当前用户的订阅"""
        return CategorySubscription.objects.filter(
            subscriber=self.request.user
        )

    def perform_create(self, serializer):
        """创建订阅时自动关联当前用户"""
        serializer.save(subscriber=self.request.user)

    def list(self, request, *args, **kwargs):
        """获取用户的订阅列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            api_response(
                success=True,
                data=serializer.data
            )
        )

    def create(self, request, *args, **kwargs):
        """订阅分类"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            api_response(
                success=True,
                data=serializer.data,
                message='订阅成功'
            ),
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """取消订阅"""
        instance = self.get_object()
        instance.delete()

        return Response(
            api_response(
                success=True,
                message='取消订阅成功'
            )
        )
