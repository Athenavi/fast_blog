"""
SQLAlchemy 模型定义 - UserActivity
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class UserActivity(Base):
    """用户活动模型模型"""
    __tablename__ = 'user_activities'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    user = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user')


    activity_type = Column(String(100), nullable=True, doc='activity_type')

    target_type = Column(String(50), nullable=True, doc='target_type')

    target_id = Column(BigInteger, doc='target_id')

    details = Column(String(255), nullable=True, doc='details')

    ip_address = Column(String(45), nullable=True, doc='ip_address')

    user_agent = Column(String(500), nullable=True, doc='user_agent')

    created_at = Column(DateTime, doc='created_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user': self.user,
            'activity_type': self.activity_type,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
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
        return f'<UserActivity id={self.id}>'
