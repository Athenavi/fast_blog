"""
SQLAlchemy 模型定义 - Category
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Integer, String,
                        Text)

from . import Base  # 使用统一的 Base


class Category(Base):
    """分类模型模型"""
    __tablename__ = 'categories'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    name = Column(String(100), nullable=True, doc='name')


    slug = Column(String(255), nullable=True, doc='slug')

    description = Column(String(255), nullable=True, doc='description')

    parent_id = Column(BigInteger, nullable=True, doc='parent_id')

    sort_order = Column(BigInteger, default=0, doc='sort_order')

    icon = Column(String(255), nullable=True, doc='icon')

    color = Column(String(255), nullable=True, doc='color')

    is_visible = Column(Boolean, default=True, doc='is_visible')

    articles_count = Column(BigInteger, doc='articles_count')

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
            'slug': self.slug,
            'description': self.description,
            'parent_id': self.parent_id,
            'sort_order': self.sort_order,
            'icon': self.icon,
            'color': self.color,
            'is_visible': self.is_visible,
            'articles_count': self.articles_count,
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
        return f'<Category id={self.id}>'
