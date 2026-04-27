"""
上传任务模型（分块上传、秒传功能）
"""
from django.conf import settings
from django.db import models


class UploadTask(models.Model):
    """上传任务模型"""
    STATUS_CHOICES = (
        ('initialized', '已初始化'),
        ('uploading', '上传中'),
        ('completed', '已完成'),
        ('canceled', '已取消'),
    )

    id = models.CharField('任务 ID', max_length=36, primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='upload_tasks',
        db_column='user_id'
    )
    filename = models.CharField('文件名', max_length=255)
    total_size = models.BigIntegerField('文件总大小')
    total_chunks = models.IntegerField('总分块数')
    uploaded_chunks = models.IntegerField('已上传分块数', default=0)
    file_hash = models.CharField('文件哈希', max_length=64, blank=True, null=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='initialized')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'upload_tasks'
        verbose_name = '上传任务'
        verbose_name_plural = '上传任务'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['status']),
            models.Index(fields=['file_hash']),
        ]

    def __str__(self):
        return f"{self.filename} ({self.status})"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'total_size': self.total_size,
            'total_chunks': self.total_chunks,
            'uploaded_chunks': self.uploaded_chunks,
            'file_hash': self.file_hash,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UploadChunk(models.Model):
    """上传分块模型"""
    id = models.AutoField(primary_key=True)
    upload_task = models.ForeignKey(
        UploadTask,
        on_delete=models.CASCADE,
        related_name='chunks',
        db_column='upload_id'
    )
    chunk_index = models.IntegerField('分块索引')
    chunk_hash = models.CharField('分块哈希', max_length=64)
    chunk_size = models.IntegerField('分块大小')
    chunk_path = models.CharField('分块路径', max_length=500)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'upload_chunks'
        verbose_name = '上传分块'
        verbose_name_plural = '上传分块'
        ordering = ['upload_task', 'chunk_index']
        unique_together = ['upload_task', 'chunk_index']
        indexes = [
            models.Index(fields=['upload_task']),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.upload_task.filename}"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'upload_id': self.upload_task.id if self.upload_task else None,
            'chunk_index': self.chunk_index,
            'chunk_hash': self.chunk_hash,
            'chunk_size': self.chunk_size,
            'chunk_path': self.chunk_path,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
