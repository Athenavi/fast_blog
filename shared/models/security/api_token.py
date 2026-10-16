"""
SQLAlchemy 模型定义 - ApiToken
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-10-12 22:06:10
"""

from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Index

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class ApiToken(Base):
    """API 令牌（第三方 / CI 接入；scopes 为权限码子集，明文只在创建时返回一次）模型"""
    __tablename__ = 'api_tokens'

    __table_args__ = (
        Index('idx_api_tokens_prefix', 'token_prefix'),
        Index('idx_api_tokens_user', 'user_id'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='令牌 ID')

    name = Column(String(100), nullable=True, doc='用途备注')

    token_prefix = Column(String(16), nullable=True, doc='明文前缀（仅用于展示与检索）')

    token_hash = Column(String(255), unique=True, nullable=True, doc='令牌哈希（argon2；不存明文）')

    scopes = Column(String(2000), nullable=True, doc='权限码子集（JSON 数组文本；空数组 = 只有默认读权限）')

    user_id = Column(BigInteger, ForeignKey('users.id'), doc='归属用户')

    expires_at = Column(DateTime, nullable=True, doc='过期时间（留空 = 不过期，不推荐）')

    last_used_at = Column(DateTime, nullable=True, doc='最近使用时间')

    is_active = Column(Boolean, default=True, doc='是否启用')

    created_at = Column(DateTime, doc='创建时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'token_prefix': self.token_prefix,
            'token_hash': self.token_hash,
            'scopes': self.scopes,
            'user_id': self.user_id,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<ApiToken id={self.id}>'
