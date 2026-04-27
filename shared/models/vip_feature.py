"""
SQLAlchemy 模型定义 - VIPFeature
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, Integer,
                        String, Text)

from . import Base  # 使用统一的 Base


class VIPFeature(Base):
    """VIP 功能特权模型模型"""
    __tablename__ = 'vip_features'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    code = Column(String(50), nullable=True, doc='code')


    name = Column(String(100), nullable=True, doc='name')

    description = Column(String(255), nullable=True, doc='description')

    required_level = Column(Integer, default=1, doc='required_level')

    is_active = Column(Boolean, default=True, doc='is_active')

    created_at = Column(DateTime, doc='created_at')




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
            'required_level': self.required_level,
            'is_active': self.is_active,
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
        return f'<VIPFeature id={self.id}>'
