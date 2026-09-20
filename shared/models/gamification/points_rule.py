"""
SQLAlchemy 模型定义 - PointsRule
手写模型（T5-11 批次 12），写法对齐代码生成器产物。

积分**规则**：v2 把它写成类内常量（`_rules` 字典），这里改为**入库可配**
（`daily_limit` 用于防刷：同一动作每日最多计入几次，0 表示不限）。
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, Integer, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class PointsRule(Base):
    """积分规则模型"""
    __tablename__ = 'points_rules'

    __table_args__ = (Index('idx_points_rules_action', 'action', unique=True),)

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='规则 ID')

    action = Column(String(50), nullable=False, doc='动作标识（唯一，如 daily_checkin）')

    points = Column(Integer, doc='该动作的积分值（负数为扣减）')

    description = Column(String(255), nullable=True, doc='说明')

    daily_limit = Column(Integer, default=0, doc='每日最多计入次数（0 = 不限）')

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
            'action': self.action,
            'points': self.points,
            'description': self.description,
            'daily_limit': self.daily_limit,
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
        return f'<PointsRule action={self.action} points={self.points}>'
