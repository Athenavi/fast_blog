"""
SQLAlchemy 模型定义 - AdminSettings
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-06-13 23:12:16
"""

from sqlalchemy import Column, BigInteger, Text, DateTime, ForeignKey, Index

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class AdminSettings(Base):
    """管理员设置模型"""
    __tablename__ = 'admin_settings'


    __table_args__ = (
        Index('idx_admin_settings_user', 'user'),
    )


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='设置 ID')

    user = Column(BigInteger, ForeignKey('users.id'), doc='用户')


    settings_data = Column(Text, doc='设置数据')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')


    def to_dict(self, exclude_sensitive: bool = False) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user': self.user,
            'settings_data': self.settings_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
