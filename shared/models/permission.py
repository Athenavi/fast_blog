"""
SQLAlchemy 模型定义 - Permission
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-05-12 10:53:12
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Index

from . import Base  # 使用统一的 Base


class Permission(Base):
    """权限模型模型"""
    __tablename__ = 'permissions'

    __table_args__ = (
        Index('idx_permissions_code', 'code'),
        Index('idx_permissions_resource', 'resource_type', 'action'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='权限 ID')

    name = Column(String(100), unique=True, nullable=True, doc='权限名称')

    code = Column(String(100), unique=True, nullable=True, doc='权限代码')

    description = Column(Text, nullable=True, doc='权限描述')

    resource_type = Column(String(50), nullable=True, doc='资源类型')

    action = Column(String(20), nullable=True, doc='操作类型')

    is_active = Column(Boolean, default=True, doc='是否激活')

    created_at = Column(DateTime, doc='创建时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'resource_type': self.resource_type,
            'action': self.action,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Permission id={self.id}>'
