"""
SQLAlchemy 模型定义 - MenuLocationAssignment
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)

from . import Base  # 使用统一的 Base


class MenuLocationAssignment(Base):
    """菜单-位置关联表模型"""
    __tablename__ = 'menu_location_assignments'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    menu_id = Column(BigInteger, ForeignKey('menus.id'), nullable=False, doc='menu_id')


    location_id = Column(BigInteger, ForeignKey('menu_locations.id'), nullable=False, doc='location_id')


    created_at = Column(DateTime, doc='created_at')


    __table_args__ = (

    Index('idx_menu_location_menu_id', 'menu_id'),
        Index('idx_menu_location_location_id', 'location_id'),
        Index('idx_menu_location_unique', 'menu_id', 'location_id', unique=True),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'menu_id': self.menu_id,
            'location_id': self.location_id,
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
        return f'<MenuLocationAssignment id={self.id}>'
