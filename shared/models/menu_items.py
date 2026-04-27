"""
SQLAlchemy 模型定义 - MenuItems
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, Index,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class MenuItems(Base):
    """菜单项模型模型"""
    __tablename__ = 'menu_items'


    id = Column(Integer, primary_key=True, autoincrement=True, doc='id')


    menu_id = Column(Integer, doc='menu_id')


    parent_id = Column(Integer, nullable=True, doc='parent_id')


    title = Column(String(255), nullable=True, doc='title')

    url = Column(String(500), nullable=True, doc='url')

    target = Column(String(255), default='_self', doc='target')

    order_index = Column(Integer, default=0, doc='order_index')

    is_active = Column(Boolean, default=True, doc='is_active')

    created_at = Column(DateTime, doc='created_at')


    __table_args__ = (

    Index('idx_menu_items_menu_id', 'menu_id'),
        Index('idx_menu_items_parent_id', 'parent_id'),
        Index('idx_menu_items_order', 'order_index'),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'menu_id': self.menu_id,
            'parent_id': self.parent_id,
            'title': self.title,
            'url': self.url,
            'target': self.target,
            'order_index': self.order_index,
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
        return f'<MenuItems id={self.id}>'
