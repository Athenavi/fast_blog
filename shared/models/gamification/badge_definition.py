"""
SQLAlchemy 模型定义 - BadgeDefinition
手写模型（T5-11 批次 12），写法对齐代码生成器产物。

勋章**定义**：v2 的 18 个内置徽章是类内常量，这里改为**入库**（作为种子数据）。

``condition_type`` + ``condition_value`` 决定自动授予条件；``is_manual=True`` 的
（如 ``verified_expert``）**只能手工授予**，check-and-award 会跳过。
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, Integer, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class BadgeDefinition(Base):
    """勋章定义模型"""
    __tablename__ = 'badge_definitions'

    __table_args__ = (
        Index('idx_badge_definitions_key', 'badge_key', unique=True),
        Index('idx_badge_definitions_category', 'category'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='勋章 ID')

    badge_key = Column(String(50), nullable=False, doc='勋章标识（唯一）')

    name = Column(String(100), nullable=False, doc='名称')

    description = Column(String(255), nullable=True, doc='说明')

    category = Column(String(50), nullable=True, doc='分类')

    icon = Column(String(100), nullable=True, doc='图标名')

    points_reward = Column(Integer, default=0, doc='获得时奖励的积分')

    condition_type = Column(String(50), nullable=True, doc='条件类型')

    condition_value = Column(Integer, default=0, doc='条件阈值')

    is_manual = Column(Boolean, default=False, doc='是否仅可手工授予')

    is_active = Column(Boolean, default=True, doc='是否启用')

    sort_order = Column(Integer, default=0, doc='排序')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'badge_key': self.badge_key,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'icon': self.icon,
            'points_reward': self.points_reward,
            'condition_type': self.condition_type,
            'condition_value': self.condition_value,
            'is_manual': self.is_manual,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
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
        return f'<BadgeDefinition badge_key={self.badge_key}>'
