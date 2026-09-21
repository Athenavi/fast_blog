"""
SQLAlchemy 模型定义 - PublishLog
手写模型（2026-09-21 批次 18：多平台发布底座），写法对齐代码生成器产物。

**发布尝试记录**：每执行一次（首次发布 / 手动重试）追加一条，成功失败都记。
任务表只保留"最后一次结果"，历史在日志里 —— 排查"为什么这次没发出去"要看的正是它。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Text

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class PublishLog(Base):
    """发布尝试记录模型"""
    __tablename__ = 'publish_logs'

    __table_args__ = (
        Index('idx_publish_logs_task_created', 'task_id', 'created_at'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='日志 ID')

    task_id = Column(
        BigInteger,
        ForeignKey('publish_tasks.id', ondelete='CASCADE'),
        nullable=False,
        doc='发布任务 ID（任务删除时日志一并删除）',
    )

    status = Column(String(20), nullable=False, doc='本次结果：success / failed')

    message = Column(Text, nullable=True, doc='结果说明 / 错误信息')

    duration_ms = Column(Integer, nullable=True, doc='本次耗时（毫秒）')

    created_at = Column(DateTime, doc='创建时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'task_id': self.task_id,
            'status': self.status,
            'message': self.message,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<PublishLog id={self.id} task={self.task_id} status={self.status}>'
