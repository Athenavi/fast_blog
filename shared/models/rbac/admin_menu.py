"""
SQLAlchemy 模型定义 - AdminMenu
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-09-18 15:49:14
"""

from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class AdminMenu(Base):
    """后台管理菜单模型（菜单级授权载体：目录/菜单/按钮三级，code 与前端路由 meta.menuCode 对应）模型"""
    __tablename__ = 'admin_menus'

    __table_args__ = (
        UniqueConstraint('code', name='idx_admin_menus_code'),
        Index('idx_admin_menus_code', 'code', unique=True),
        Index('idx_admin_menus_parent', 'parent_id'),
        Index('idx_admin_menus_active', 'is_active'),
        Index('idx_admin_menus_sort', 'sort_order'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='菜单 ID')

    code = Column(String(100), unique=True, nullable=True, doc='菜单稳定标识（与前端路由 meta.menuCode 一一对应）')

    title = Column(String(100), nullable=True, doc='菜单名称')

    parent_id = Column(BigInteger, ForeignKey('admin_menus.id'), nullable=True,
                       doc='父菜单 ID（目录/菜单/按钮的树形层级）')

    menu_type = Column(Integer, default=2, doc='菜单类型（1 目录 / 2 菜单 / 3 按钮）')

    permission_code = Column(String(100), nullable=True, doc='关联权限码（按钮级通常填写，与 capabilities.code 同构）')

    sort_order = Column(BigInteger, default=0, doc='显示排序')

    is_active = Column(Boolean, default=True, doc='是否激活')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'code': self.code,
            'title': self.title,
            'parent_id': self.parent_id,
            'menu_type': self.menu_type,
            'permission_code': self.permission_code,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AdminMenu id={self.id}>'
