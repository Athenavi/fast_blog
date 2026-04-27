"""
SQLAlchemy 模型定义 - VIPPlan
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, Integer,
                        Numeric, String, Text)

from . import Base  # 使用统一的 Base


class VIPPlan(Base):
    """VIP 套餐模型模型"""
    __tablename__ = 'vip_plans'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    name = Column(String(100), nullable=True, doc='name')


    description = Column(String(255), nullable=True, doc='description')

    price = Column(Numeric(10, 2), doc='price')

    original_price = Column(Numeric(10, 2), nullable=True, doc='original_price')

    duration_days = Column(Integer, doc='duration_days')

    level = Column(BigInteger, default=1, doc='level')

    features = Column(String(255), nullable=True, doc='features')

    is_active = Column(Boolean, default=True, doc='is_active')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'original_price': self.original_price,
            'duration_days': self.duration_days,
            'level': self.level,
            'features': self.features,
            'is_active': self.is_active,
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
        return f'<VIPPlan id={self.id}>'
