"""
AI 配置模型 — 用户 AI 助手配置（最多 10 条/用户）
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from shared.models import Base


class AIConfig(Base):
    __tablename__ = 'ai_configs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(100), nullable=False, comment='配置名称')
    api_url = Column(String(500), nullable=False, comment='API 端点 URL')
    api_key_encrypted = Column(Text, nullable=False, comment='加密后的 API Key')
    model = Column(String(100), nullable=False, comment='模型名称')
    provider = Column(String(50), nullable=False, default='openai', comment='提供商')
    is_active = Column(Boolean, nullable=False, default=False, comment='是否激活')
    sort_order = Column(Integer, nullable=False, default=0, comment='排序')
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)

    user = relationship('User', backref='ai_configs')

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_ai_config_user_name'),
        {'comment': '用户 AI 配置表'}
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'api_url': self.api_url,
            'model': self.model,
            'provider': self.provider,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
