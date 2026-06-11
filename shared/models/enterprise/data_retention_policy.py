"""
SQLAlchemy 模型定义 - DataRetentionPolicy
数据保留策略模型，用于配置和管理各类数据的保留期限及到期处理动作。
"""

from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, Index

from .. import Base  # 使用统一的 Base


class DataRetentionPolicy(Base):
    """数据保留策略模型"""
    __tablename__ = 'data_retention_policies'

    __table_args__ = (
        Index('idx_drp_data_category', 'data_category'),
        Index('idx_drp_is_active', 'is_active'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='策略 ID')

    data_category = Column(String(50), nullable=False, doc='数据类别 (如: audit_log, notification, analytics)')

    retention_days = Column(Integer, nullable=False, doc='保留天数')

    action = Column(String(50), nullable=False, default='delete', doc='到期动作 (delete/archive)')

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
            'data_category': self.data_category,
            'retention_days': self.retention_days,
            'action': self.action,
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
        return f'<DataRetentionPolicy id={self.id} category={self.data_category}>'
