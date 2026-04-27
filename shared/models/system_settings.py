"""
SQLAlchemy 模型定义 - SystemSettings
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, Integer,
                        String, Text)

from . import Base  # 使用统一的 Base


class SystemSettings(Base):
    """系统设置模型模型"""
    __tablename__ = 'system_settings'


    id = Column(Integer, primary_key=True, autoincrement=True, doc='id')


    setting_key = Column(String(100), nullable=True, doc='setting_key')


    setting_value = Column(String(255), nullable=True, doc='setting_value')

    setting_type = Column(String(255), default='string', doc='setting_type')

    description = Column(String(255), nullable=True, doc='description')

    is_public = Column(Boolean, default=False, doc='is_public')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'setting_type': self.setting_type,
            'description': self.description,
            'is_public': self.is_public,
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
        return f'<SystemSettings id={self.id}>'
