"""
媒体文件序列化器
"""
from rest_framework import serializers

from apps.media.models import Media


class MediaSerializer(serializers.ModelSerializer):
    """媒体文件序列化器"""
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = (
            'id', 'user_id', 'filename', 'original_filename',
            'file_path', 'file_url', 'file_size', 'file_size_mb',
            'file_type', 'mime_type', 'width', 'height', 'duration',
            'thumbnail_path', 'thumbnail_url', 'description', 'alt_text',
            'is_public', 'download_count', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'user_id', 'file_size', 'file_size_mb', 'created_at', 'updated_at'
        )

    def get_file_size_mb(self, obj):
        """获取文件大小 (MB)"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0

    def create(self, validated_data):
        """创建媒体文件"""
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)
