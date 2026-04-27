"""
SQLAlchemy 模型定义 - UserRole
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)

from . import Base  # 使用统一的 Base


class UserRole(Base):
    """用户角色关联模型模型"""
    __tablename__ = 'user_role_assignments'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user_id')


    role_id = Column(BigInteger, ForeignKey('roles.id'), nullable=False, doc='role_id')


    assigned_by = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='assigned_by')

    created_at = Column(DateTime, doc='created_at')


    __table_args__ = (

    Index('idx_user_roles_user_id', 'user_id'),
        Index('idx_user_roles_role_id', 'role_id'),
        Index('idx_user_roles_unique', 'user_id', 'role_id', unique=True),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'role_id': self.role_id,
            'assigned_by': self.assigned_by,
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
        return f'<UserRole id={self.id}>'
