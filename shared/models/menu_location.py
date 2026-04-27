"""
SQLAlchemy 模型定义 - MenuLocation
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, Index,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class MenuLocation(Base):
    """菜单位置模型（主菜单、页脚菜单等）模型"""
    __tablename__ = 'menu_locations'


    id = Column(Integer, primary_key=True, autoincrement=True, doc='id')


    name = Column(String(100), nullable=True, doc='name')


    slug = Column(String(100), unique=True, nullable=True, doc='slug')


    description = Column(String(255), nullable=True, doc='description')

    theme_supports = Column(String(255), nullable=True, doc='theme_supports')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')

    __table_args__ = (

    Index('idx_menu_locations_slug', 'slug', unique=True),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'theme_supports': self.theme_supports,
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
        return f'<MenuLocation id={self.id}>'
