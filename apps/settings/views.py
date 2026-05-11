"""
系统设置视图
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settings.models import SystemSettings, AdminSettings
from django_blog.exceptions import api_response


class SystemSettingsView(APIView):
    """系统设置视图"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        """获取所有系统设置"""
        settings = SystemSettings.objects.all()

        settings_data = {}
        for setting in settings:
            if setting.is_public or request.user.is_superuser:
                settings_data[setting.setting_key] = setting.get_typed_value()

        return Response(
            api_response(
                success=True,
                data=settings_data
            )
        )

    def post(self, request):
        """更新或创建系统设置"""
        setting_key = request.data.get('setting_key')

        if not setting_key:
            return Response(
                api_response(
                    success=False,
                    error='缺少 setting_key 参数'
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        setting, created = SystemSettings.objects.update_or_create(
            setting_key=setting_key,
            defaults={
                'setting_value': str(request.data.get('setting_value', '')),
                'setting_type': request.data.get('setting_type', 'string'),
                'description': request.data.get('description', ''),
                'is_public': request.data.get('is_public', False)
            }
        )

        return Response(
            api_response(
                success=True,
                data=setting.to_dict(),
                message='设置保存成功'
            )
        )


class AdminSettingsView(generics.RetrieveUpdateAPIView):
    """管理员个人设置"""
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """获取或创建管理员设置"""
        settings, created = AdminSettings.objects.get_or_create(
            user=self.request.user,
            defaults={'settings_data': {}}
        )
        return settings

    def retrieve(self, request, *args, **kwargs):
        """获取管理员设置"""
        instance = self.get_object()
        return Response(
            api_response(
                success=True,
                data=instance.to_dict()
            )
        )

    def update(self, request, *args, **kwargs):
        """更新管理员设置"""
        instance = self.get_object()
        instance.settings_data = request.data.get('settings_data', {})
        instance.save()

        return Response(
            api_response(
                success=True,
                data=instance.to_dict(),
                message='设置更新成功'
            )
        )
