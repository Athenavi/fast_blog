"""
SQLAlchemy 模型定义 - RoleAdminMenu
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-09-18 15:49:14
"""

from sqlalchemy import Column, BigInteger, DateTime, ForeignKey, Index, UniqueConstraint

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class RoleAdminMenu(Base):
    """角色-后台菜单关联模型（菜单级授权）模型"""
    __tablename__ = 'role_admin_menus'

    __table_args__ = (
        UniqueConstraint('role_id', 'admin_menu_id', name='idx_role_admin_menus_unique'),
        Index('idx_role_admin_menus_role', 'role_id'),
        Index('idx_role_admin_menus_menu', 'admin_menu_id'),
        Index('idx_role_admin_menus_unique', 'role_id', 'admin_menu_id', unique=True),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='关联 ID')

    role_id = Column(BigInteger, ForeignKey('roles.id'), doc='角色 ID')

    admin_menu_id = Column(BigInteger, ForeignKey('admin_menus.id'), doc='菜单 ID')

    created_at = Column(DateTime, doc='授权时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'role_id': self.role_id,
            'admin_menu_id': self.admin_menu_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<RoleAdminMenu id={self.id}>'
