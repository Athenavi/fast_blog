"""
媒体文件视图
"""
import os

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import viewsets, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.media.models import Media
from apps.media.serializers import MediaSerializer
from django_blog.exceptions import api_response
from shared.services.svg_service import SVGService
from shared.services.image_tool import ExifService
from shared.services.pdf_service import PDFService


class MediaViewSet(viewsets.ModelViewSet):
    """媒体文件视图集"""
    queryset = Media.objects.select_related('user').all()
    serializer_class = MediaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['file_type', 'is_public', 'user_id']
    search_fields = ['filename', 'original_filename', 'description']
    ordering_fields = ['created_at', 'file_size', 'download_count']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        """根据操作返回不同的权限"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        """自定义查询集"""
        queryset = super().get_queryset()

        # 非管理员只能查看公开文件
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_public=True)

        return queryset

    def perform_create(self, serializer):
        """保存媒体文件"""
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """上传媒体文件"""
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            api_response(
                success=True,
                data=serializer.data,
                message='文件上传成功'
            ),
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """删除媒体文件"""
        instance = self.get_object()

        # 删除物理文件
        try:
            if os.path.exists(instance.file_path):
                os.remove(instance.file_path)

            # 删除缩略图
            if instance.thumbnail_path and os.path.exists(instance.thumbnail_path):
                os.remove(instance.thumbnail_path)
        except Exception as e:
            pass

        instance.delete()

        return Response(
            api_response(
                success=True,
                message='文件删除成功'
            )
        )


class MediaUploadView(APIView):
    """媒体文件上传视图"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        """上传文件"""
        file_obj = request.FILES.get('file')

        if not file_obj:
            return Response(
                api_response(
                    success=False,
                    error='没有上传文件'
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查是否为 SVG 文件
        is_svg = file_obj.content_type == 'image/svg+xml' or file_obj.name.lower().endswith('.svg')
        is_pdf = file_obj.content_type == 'application/pdf' or file_obj.name.lower().endswith('.pdf')
        
        if is_svg:
            # 使用 SVG 服务处理
            is_valid, error_msg = SVGService.validate_upload(file_obj)
            if not is_valid:
                return Response(
                    api_response(
                        success=False,
                        error=error_msg
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 生成保存路径
            from django.utils import timezone
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'svg')
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{file_obj.name}"
            save_path = os.path.join(upload_dir, filename)
            
            # 处理并保存 SVG
            try:
                result = SVGService.process_svg(file_obj, save_path)
                file_url = f"/media/uploads/svg/{filename}"
                
                # 创建媒体记录
                media = Media.objects.create(
                    user=request.user,
                    filename=filename,
                    original_filename=file_obj.name,
                    file_path=save_path,
                    file_url=file_url,
                    file_size=result['file_size'],
                    file_type='image',
                    mime_type='image/svg+xml',
                    width=result['metadata'].get('width'),
                    height=result['metadata'].get('height'),
                    description=f"SVG 图像 ({result['metadata'].get('total_elements', 0)} 个元素)"
                )
                
                serializer = MediaSerializer(media, context={'request': request})
                
                return Response(
                    api_response(
                        success=True,
                        data=serializer.data,
                        message='SVG 文件上传成功'
                    ),
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    api_response(
                        success=False,
                        error=f'SVG 处理失败: {str(e)}'
                    ),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # 处理 PDF 文件
        if is_pdf:
            # 验证 PDF
            is_valid, error_msg = PDFService.validate_upload(file_obj)
            if not is_valid:
                return Response(
                    api_response(
                        success=False,
                        error=error_msg
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 生成保存路径
            from django.utils import timezone
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'pdf')
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{file_obj.name}"
            save_path = os.path.join(upload_dir, filename)
            
            # 确保目录存在
            os.makedirs(upload_dir, exist_ok=True)
            
            # 保存文件
            with open(save_path, 'wb+') as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)
            
            # 提取 PDF 元数据
            try:
                metadata = PDFService.extract_metadata(save_path)
                description_parts = []
                if metadata.get('title'):
                    description_parts.append(metadata['title'])
                if metadata.get('page_count') and metadata['page_count'] > 0:
                    description_parts.append(f"{metadata['page_count']} 页")
                if metadata.get('author'):
                    description_parts.append(f"作者: {metadata['author']}")
                
                description = ' | '.join(description_parts) if description_parts else 'PDF 文档'
            except Exception:
                description = 'PDF 文档'
            
            # 尝试生成缩略图
            thumbnail_path = None
            thumbnail_url = None
            try:
                thumb_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails', 'pdf')
                os.makedirs(thumb_dir, exist_ok=True)
                thumb_filename = f"{os.path.splitext(filename)[0]}.jpg"
                thumb_save_path = os.path.join(thumb_dir, thumb_filename)
                
                if PDFService.generate_thumbnail(save_path, thumb_save_path):
                    thumbnail_path = thumb_save_path
                    thumbnail_url = f"/media/thumbnails/pdf/{thumb_filename}"
            except Exception:
                pass
            
            file_url = f"/media/uploads/pdf/{filename}"
            
            # 创建媒体记录
            media = Media.objects.create(
                user=request.user,
                filename=filename,
                original_filename=file_obj.name,
                file_path=save_path,
                file_url=file_url,
                file_size=file_obj.size,
                file_type='document',
                mime_type='application/pdf',
                description=description,
                thumbnail_path=thumbnail_path,
                thumbnail_url=thumbnail_url
            )
            
            serializer = MediaSerializer(media, context={'request': request})
            
            return Response(
                api_response(
                    success=True,
                    data=serializer.data,
                    message='PDF 文件上传成功'
                ),
                status=status.HTTP_201_CREATED
            )

        # 检查文件大小（非 SVG/PDF）
        max_size = getattr(settings, 'UPLOAD_LIMIT', 62914560)
        if file_obj.size > max_size:
            return Response(
                api_response(
                    success=False,
                    error=f'文件大小超过限制 ({max_size / 1024 / 1024:.0f}MB)'
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        # 创建媒体记录（非 SVG）
        media = Media.objects.create(
            user=request.user,
            filename=file_obj.name,
            original_filename=file_obj.name,
            file_path=file_obj.file.path if hasattr(file_obj, 'file') else '',
            file_url='',  # 后续填充
            file_size=file_obj.size,
            file_type=self.get_file_type(file_obj.content_type),
            mime_type=file_obj.content_type
        )
        
        # 如果是图片，尝试提取 EXIF 数据
        if self.get_file_type(file_obj.content_type) == 'image':
            try:
                file_path = file_obj.file.path if hasattr(file_obj, 'file') else ''
                if file_path and os.path.exists(file_path):
                    exif_data = ExifService.extract_exif(file_path)
                    if ExifService.has_significant_exif(exif_data):
                        # 将 EXIF 信息保存到 description 字段
                        camera_info = []
                        if exif_data.get('camera', {}).get('model'):
                            camera_info.append(exif_data['camera']['model'])
                        if exif_data.get('settings', {}).get('aperture'):
                            camera_info.append(exif_data['settings']['aperture'])
                        if exif_data.get('settings', {}).get('shutter_speed'):
                            camera_info.append(exif_data['settings']['shutter_speed'])
                        if exif_data.get('settings', {}).get('iso'):
                            camera_info.append(f"ISO {exif_data['settings']['iso']}")
                        
                        if camera_info:
                            media.description = ' | '.join(camera_info)
                            media.save(update_fields=['description'])
            except Exception:
                # EXIF 提取失败不影响上传
                pass

        serializer = MediaSerializer(media, context={'request': request})

        return Response(
            api_response(
                success=True,
                data=serializer.data,
                message='文件上传成功'
            )
        )

    def get_file_type(self, content_type):
        """根据 MIME 类型判断文件类型"""
        if content_type.startswith('image/'):
            return 'image'
        elif content_type.startswith('video/'):
            return 'video'
        elif content_type.startswith('audio/'):
            return 'audio'
        elif content_type.startswith('application/'):
            return 'document'
        return 'other'
