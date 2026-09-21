"""
SQLAlchemy 模型定义 - PublishTask
手写模型（2026-09-21 批次 18：多平台发布底座），写法对齐代码生成器产物。

**发布任务**：一条记录 = 「一篇文章 → 一个渠道」的一次发布意图。
同一 (文章, 渠道) 只有一条任务（唯一索引），**重试复用同一条** —— 这样"这篇发过没"
永远看得到，也不会因为反复重试堆出一串脏记录。

``payload`` 是**发布载荷快照**（标题 / 摘要 / 正文 / 永久链接的 JSON）：重试时用同一份，
保证可复现（期间文章被改动也不会让重试发出另一份内容）。

`status` 取值：``pending``（待执行）/ ``publishing``（执行中）/ ``success`` / ``failed``。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Text

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class PublishTask(Base):
    """第三方发布任务模型"""
    __tablename__ = 'publish_tasks'

    __table_args__ = (
        Index('idx_publish_tasks_article_channel', 'article_id', 'channel_id', unique=True),
        Index('idx_publish_tasks_status_created', 'status', 'created_at'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='任务 ID')

    article_id = Column(
        BigInteger,
        ForeignKey('articles.id', ondelete='CASCADE'),
        nullable=False,
        doc='文章 ID（文章删除时任务一并删除）',
    )

    channel_id = Column(
        BigInteger,
        ForeignKey('publish_channels.id', ondelete='CASCADE'),
        nullable=False,
        doc='渠道 ID（渠道删除时任务一并删除）',
    )

    status = Column(String(20), default='pending', doc='状态：pending / publishing / success / failed')

    attempts = Column(Integer, default=0, doc='已尝试次数（含手动重试）')

    last_error = Column(String(500), nullable=True, doc='最近一次失败原因（成功时清空）')

    external_id = Column(String(128), nullable=True, doc='平台侧文档 ID')

    external_url = Column(String(500), nullable=True, doc='平台侧链接')

    payload = Column(Text, nullable=True, doc='发布载荷快照（JSON）')

    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='创建人 ID')

    started_at = Column(DateTime, nullable=True, doc='最近一次开始时间')

    finished_at = Column(DateTime, nullable=True, doc='最近一次结束时间')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'article_id': self.article_id,
            'channel_id': self.channel_id,
            'status': self.status,
            'attempts': int(self.attempts or 0),
            'last_error': self.last_error,
            'external_id': self.external_id,
            'external_url': self.external_url,
            'payload': self.payload,
            'created_by': self.created_by,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<PublishTask id={self.id} article={self.article_id} channel={self.channel_id}>'
