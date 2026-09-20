"""
SQLAlchemy 模型定义 - PointsTransaction
手写模型（T5-11 批次 12），写法对齐代码生成器产物。

积分**流水**：每次变动都记一条，并写清 `balance_after`（便于对账与「我的流水」展示）。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class PointsTransaction(Base):
    """积分流水模型"""
    __tablename__ = 'points_transactions'

    __table_args__ = (
        Index('idx_points_tx_user_created', 'user_id', 'created_at'),
        Index('idx_points_tx_action', 'action'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='流水 ID')

    user_id = Column(BigInteger, ForeignKey('users.id'), doc='用户 ID')

    amount = Column(Integer, doc='变动值（正数为获得，负数为消耗）')

    balance_after = Column(Integer, doc='变动后余额')

    action = Column(String(50), doc='动作标识（daily_checkin / admin_grant / exchange …）')

    description = Column(String(255), nullable=True, doc='说明')

    reference_id = Column(BigInteger, nullable=True, doc='关联记录 ID')

    reference_type = Column(String(50), nullable=True, doc='关联记录类型')

    created_at = Column(DateTime, doc='发生时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'balance_after': self.balance_after,
            'action': self.action,
            'description': self.description,
            'reference_id': self.reference_id,
            'reference_type': self.reference_type,
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
        return f'<PointsTransaction id={self.id} amount={self.amount}>'
