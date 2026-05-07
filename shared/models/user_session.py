"""
SQLAlchemy 模型定义 - UserSession
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-05-07 16:38:48
"""

from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, ForeignKey

from . import Base  # 使用统一的 Base

from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, ForeignKey, Index

class UserSession(Base):
    """用户会话模型模型"""
    __tablename__ = 'user_sessions'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user_id')


    session_token = Column(String(255), unique=True, nullable=True, doc='session_token')


    device_info = Column(String(500), nullable=True, doc='device_info')


    ip_address = Column(String(45), nullable=True, doc='ip_address')


    location = Column(String(100), nullable=True, doc='location')


    is_active = Column(Boolean, default=True, doc='is_active')

    last_activity = Column(DateTime, doc='last_activity')

    expires_at = Column(DateTime, doc='expires_at')

    created_at = Column(DateTime, doc='created_at')

    __table_args__ = (

        Index('idx_user_sessions_user_id', 'user_id'),
        Index('idx_user_sessions_token', 'session_token', unique=True),
        Index('idx_user_sessions_is_active', 'is_active'),
        Index('idx_user_sessions_expires', 'expires_at'),
    )

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'device_info': self.device_info,
            'ip_address': self.ip_address,
            'location': self.location,
            'is_active': self.is_active,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<UserSession id={self.id}>'
