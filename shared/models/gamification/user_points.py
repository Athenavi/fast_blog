"""
SQLAlchemy 模型定义 - UserPoints
手写模型（T5-11 批次 12），写法对齐代码生成器产物。

用户积分**账户**（一人一行）：余额 + 累计获得/消耗 + 最后签到时间（签到去重用）。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, Index

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class UserPoints(Base):
    """用户积分账户模型"""
    __tablename__ = 'user_points'

    __table_args__ = (
        Index('idx_user_points_user', 'user_id', unique=True),
        Index('idx_user_points_balance', 'balance'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='账户 ID')

    user_id = Column(BigInteger, ForeignKey('users.id'), doc='用户 ID')

    balance = Column(Integer, default=0, doc='当前可用积分')

    total_earned = Column(Integer, default=0, doc='累计获得')

    total_spent = Column(Integer, default=0, doc='累计消耗')

    last_checkin_at = Column(DateTime, nullable=True, doc='最后签到时间（每日签到去重）')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'balance': self.balance,
            'total_earned': self.total_earned,
            'total_spent': self.total_spent,
            'last_checkin_at': self.last_checkin_at.isoformat() if self.last_checkin_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<UserPoints id={self.id} balance={self.balance}>'
