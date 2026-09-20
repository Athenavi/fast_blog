"""
SQLAlchemy 模型定义 - UserBadge
手写模型（T5-11 批次 12），写法对齐代码生成器产物。

用户**已获**勋章：``(user_id, badge_key)`` 唯一（授予接口幂等）。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class UserBadge(Base):
    """用户已获勋章模型"""
    __tablename__ = 'user_badges'

    __table_args__ = (
        Index('idx_user_badges_unique', 'user_id', 'badge_key', unique=True),
        Index('idx_user_badges_badge', 'badge_key'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='记录 ID')

    user_id = Column(BigInteger, ForeignKey('users.id'), doc='用户 ID')

    badge_key = Column(String(50), nullable=False, doc='勋章标识')

    awarded_at = Column(DateTime, doc='获得时间')

    awarded_by = Column(BigInteger, nullable=True, doc='手工授予时的管理员 ID')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'badge_key': self.badge_key,
            'awarded_at': self.awarded_at.isoformat() if self.awarded_at else None,
            'awarded_by': self.awarded_by,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<UserBadge user={self.user_id} badge={self.badge_key}>'
