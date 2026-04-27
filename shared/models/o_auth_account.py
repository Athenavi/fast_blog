"""
SQLAlchemy 模型定义 - OAuthAccount
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)

from . import Base  # 使用统一的 Base


class OAuthAccount(Base):
    """OAuth 第三方登录账号关联模型模型"""
    __tablename__ = 'oauth_accounts'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user_id')


    provider = Column(String(50), index=True, nullable=True, doc='provider')


    provider_user_id = Column(String(255), index=True, nullable=True, doc='provider_user_id')

    access_token = Column(String(255), nullable=True, doc='access_token')

    refresh_token = Column(String(255), nullable=True, doc='refresh_token')

    token_expires_at = Column(DateTime, nullable=True, doc='token_expires_at')

    extra_data = Column(String(255), nullable=True, doc='extra_data')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_oauth_accounts_provider_user', 'provider', 'provider_user_id', unique=True),
        Index('idx_oauth_accounts_user_provider', 'user_id', 'provider', unique=True),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'provider': self.provider,
            'provider_user_id': self.provider_user_id,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<OAuthAccount id={self.id}>'
