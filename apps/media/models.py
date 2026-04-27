"""
Media App Models
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-03-31 17:55:17
"""

from django.db import models

# 引入自动生成的 Mixin
from apps.generated.auto_orm import *


class FileHash(FileHashMixin, TimestampMixin):
    """文件哈希模型"""

    class Meta:
        db_table = "file_hashs"
        verbose_name = "文件哈希模型"
        verbose_name_plural = "文件哈希模型"

    def __str__(self):
        return f"{self.hash} - {self.filename}"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "hash": self.hash,
            "filename": self.filename,
            "created_at": self.created_at,
            "reference_count": self.reference_count,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "storage_path": self.storage_path
        }


class Media(MediaMixin, TimestampMixin):
    """媒体文件模型（继承自动生成的 Mixin）"""

    # 添加 hash 字段（因为 routes.yaml 中没有定义 Media 相关路由，需要手动添加）
    hash = models.CharField('文件哈希', max_length=64, default='')

    class Meta:
        db_table = "media"
        verbose_name = "媒体文件模型"
        verbose_name_plural = "媒体文件模型"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user": self.user,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_url": self.file_url,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
            "thumbnail_path": self.thumbnail_path,
            "thumbnail_url": self.thumbnail_url,
            "description": self.description,
            "alt_text": self.alt_text,
            "is_public": self.is_public,
            "download_count": self.download_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class MediaFolder(MediaFolderMixin, TimestampMixin):
    """媒体文件夹模型（继承自动生成的 Mixin）"""

    # 覆盖 parent_id 字段，使用正确的自引用
    parent_id = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        verbose_name="父文件夹",
        null=True,
        blank=True,
        related_name="children"
    )

    class Meta:
        db_table = "media_folders"
        verbose_name = "媒体文件夹"
        verbose_name_plural = "媒体文件夹"
        ordering = ['name']

    def __str__(self):
        return self.name

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id_id if self.parent_id else None,
            "user": self.user_id,
            "description": self.description,
            "is_public": self.is_public,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }