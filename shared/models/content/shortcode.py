"""
SQLAlchemy 模型定义 - Shortcode
手写模型（v3 content/shortcode 批次），写法对齐代码生成器产物
短代码库：``[code]`` -> 预定义内容片段（HTML/模板片段），参考 WordPress shortcode。
"""

from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, Index, UniqueConstraint

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class Shortcode(Base):
    """短代码模型"""
    __tablename__ = 'shortcodes'

    __table_args__ = (
        # 命名唯一约束（与最新迁移口径一致：不重复创建同名 Index）
        UniqueConstraint('code', name='idx_shortcodes_code'),
        Index('idx_shortcodes_is_active', 'is_active'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='短代码ID')

    code = Column(String(100), nullable=False, doc='短代码标识（如 ad-banner），创建后锁定')

    name = Column(String(100), nullable=False, doc='展示名')

    description = Column(String(255), nullable=True, doc='描述')

    content = Column(Text, nullable=False, doc='替换内容（HTML/模板片段）')

    is_active = Column(Boolean, default=True, doc='是否启用')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'content': self.content,
            'is_active': self.is_active,
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
        return f'<Shortcode id={self.id}>'
