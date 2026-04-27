"""
系统设置序列化器
"""
from rest_framework import serializers

from apps.settings.models import SystemSettings, AdminSettings


class SystemSettingsSerializer(serializers.ModelSerializer):
    """系统设置序列化器"""
    typed_value = serializers.SerializerMethodField()

    class Meta:
        model = SystemSettings
        fields = (
            'id', 'setting_key', 'setting_value', 'typed_value',
            'setting_type', 'description', 'is_public',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_typed_value(self, obj):
        """获取类型化的值"""
        return obj.get_typed_value()


class AdminSettingsSerializer(serializers.ModelSerializer):
    """管理员设置序列化器"""

    class Meta:
        model = AdminSettings
        fields = ('id', 'user_id', 'settings_data', 'created_at', 'updated_at')
        read_only_fields = ('user_id', 'created_at', 'updated_at')
