"""
SQLAlchemy 模型定义 - WidgetInstance
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Index, Integer,
                        String, Text)

from . import Base  # 使用统一的 Base


class WidgetInstance(Base):
    """Widget实例模型（持久化存储）模型"""
    __tablename__ = 'widget_instances'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    widget_type = Column(String(50), nullable=True, doc='widget_type')


    area = Column(String(50), nullable=True, doc='area')


    title = Column(String(255), nullable=True, doc='title')

    config = Column(String(255), nullable=True, doc='config')

    order_index = Column(BigInteger, default=0, doc='order_index')

    is_active = Column(Boolean, default=True, doc='is_active')

    conditions = Column(String(255), nullable=True, doc='conditions')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_widget_instances_area', 'area'),
        Index('idx_widget_instances_order', 'order_index'),
        Index('idx_widget_instances_type', 'widget_type'),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'widget_type': self.widget_type,
            'area': self.area,
            'title': self.title,
            'config': self.config,
            'order_index': self.order_index,
            'is_active': self.is_active,
            'conditions': self.conditions,
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
        return f'<WidgetInstance id={self.id}>'
