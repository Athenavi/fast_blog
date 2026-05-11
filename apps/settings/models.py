"""
Settings App Models
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-03-31 17:55:17
"""

# 引入自动生成的 Mixin
from apps.generated.auto_orm import *


class AdminSettings(AdminSettingsMixin, TimestampMixin):
    """管理员设置模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "admin_settingss"
        verbose_name = "管理员设置模型"
        verbose_name_plural = "管理员设置模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user,
            "settings_data": self.settings_data,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class MenuItems(MenuItemsMixin, TimestampMixin):
    """菜单项模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "menu_itemss"
        verbose_name = "菜单项模型"
        verbose_name_plural = "菜单项模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.title)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "menu_id": self.menu_id,
            "parent_id": self.parent_id,
            "title": self.title,
            "url": self.url,
            "target": self.target,
            "order_index": self.order_index,
            "is_active": self.is_active,
            "created_at": self.created_at
        }


class Menus(MenusMixin, TimestampMixin):
    """菜单模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "menuss"
        verbose_name = "菜单模型"
        verbose_name_plural = "菜单模型"
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
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class Pages(PagesMixin, TimestampMixin):
    """页面模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "pagess"
        verbose_name = "页面模型"
        verbose_name_plural = "页面模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.title)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "content": self.content,
            "excerpt": self.excerpt,
            "template": self.template,
            "status": self.status,
            "author_id": self.author_id,
            "parent_id": self.parent_id,
            "order_index": self.order_index,
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "meta_keywords": self.meta_keywords,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "published_at": self.published_at
        }


class SystemSettings(SystemSettingsMixin, TimestampMixin):
    """系统设置模型（继承自动生成的 Mixin）"""

    class Meta:
        db_table = "system_settings"
        verbose_name = "系统设置模型"
        verbose_name_plural = "系统设置模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "setting_key": self.setting_key,
            "setting_value": self.setting_value,
            "setting_type": self.setting_type,
            "description": self.description,
            "is_public": self.is_public,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
