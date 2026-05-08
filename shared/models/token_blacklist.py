"""
SQLAlchemy 模型定义 - TokenBlacklist
用于存储被撤销的 JWT Token

注意：这是一个 UNLOGGED 表，不写入 WAL，性能更高但可能在数据库崩溃或主备切换时丢失数据。
这对于临时性的 Token 黑名单是可接受的，因为 Token 本身有过期时间。
"""
from sqlalchemy import (
    Column, BigInteger, String, DateTime, Index, event, text, func
)
from . import Base  # 使用统一的 Base


class TokenBlacklist(Base):
    """Token 黑名单模型（UNLOGGED 表）"""
    __tablename__ = 'token_blacklist'

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')

    # Token 的唯一标识（使用 token 的前32个字符作为标识）
    # unique=True 会自动创建唯一索引，无需再单独指定 index=True
    token_identifier = Column(
        String(64), unique=True, nullable=False, doc='token_identifier'
    )

    # Token 哈希值（用于调试和审计，可选）
    token_hash = Column(String(128), nullable=True, doc='token_hash')

    # 过期时间
    expires_at = Column(DateTime, nullable=False, doc='expires_at')

    # 创建时间（使用数据库函数 now()，保证时区一致性）
    created_at = Column(DateTime, default=func.now(), doc='created_at')

    # 撤销原因（可选）
    reason = Column(String(255), nullable=True, doc='reason')

    __table_args__ = (
        Index('idx_token_blacklist_expires', 'expires_at'),
        Index('idx_token_blacklist_created', 'created_at'),
        {'postgresql_unlogged': True},
    )

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'token_identifier': self.token_identifier,
            'token_hash': self.token_hash,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reason': self.reason,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<TokenBlacklist id={self.id}>'
