"""
SQLAlchemy 模型定义 - Role
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Index, Integer,
                        String, Text)

from . import Base  # 使用统一的 Base


class Role(Base):
    """角色模型模型"""
    __tablename__ = 'roles'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    name = Column(String(100), nullable=True, doc='name')


    slug = Column(String(100), unique=True, nullable=True, doc='slug')


    description = Column(String(255), nullable=True, doc='description')

    permissions = Column(String(255), nullable=True, doc='permissions')

    is_system = Column(Boolean, default=False, doc='is_system')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_roles_slug', 'slug', unique=True),
        Index('idx_roles_is_system', 'is_system'),
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
            'permissions': self.permissions,
            'is_system': self.is_system,
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
        return f'<Role id={self.id}>'
