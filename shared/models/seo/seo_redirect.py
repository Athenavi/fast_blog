"""
SQLAlchemy 模型定义 - SeoRedirect
手写实现（登记在 config/models.yaml 的 ``module: seo``）

v2 的 redirect 管理是 ``redirects.json`` 文件存储（非 DB），v3 改为真表：
「迁移时按源站 URL 自动生成的 301」与「手工维护的跳转」共用同一张表。
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Index

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class SeoRedirect(Base):
    """SEO 跳转规则模型"""
    __tablename__ = 'seo_redirects'

    __table_args__ = (
        Index('idx_seo_redirects_from_path', 'from_path', unique=True),
        Index('idx_seo_redirects_active', 'is_active'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='规则 ID')

    from_path = Column(String(500), nullable=False, doc='源路径（站点相对路径，如 /old-post；导入时按源站 URL 归一）')

    to_path = Column(String(500), nullable=False, doc='目标路径或绝对 URL')

    status_code = Column(Integer, nullable=False, default=301, doc='HTTP 状态码（301 永久 / 302 临时 / 307 / 308）')

    is_active = Column(Boolean, nullable=False, default=True, doc='是否启用')

    hits = Column(BigInteger, nullable=False, default=0, doc='命中次数（由解析端点真实累加）')

    source = Column(String(50), nullable=False, default='manual', doc='来源（manual 手工维护 / migration 导入生成）')

    source_reference = Column(String(500), nullable=True, doc='来源说明（迁移任务名 / 源文件名）')

    notes = Column(Text, nullable=True, doc='备注')

    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='创建者用户 ID')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'from_path': self.from_path,
            'to_path': self.to_path,
            'status_code': self.status_code,
            'is_active': self.is_active,
            'hits': self.hits,
            'source': self.source,
            'source_reference': self.source_reference,
            'notes': self.notes,
            'created_by': self.created_by,
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
        return f'<SeoRedirect id={self.id} from={self.from_path}>'
