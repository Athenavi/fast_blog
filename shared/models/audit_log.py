"""
SQLAlchemy 模型定义 - AuditLog
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-05-21 08:12:22
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Index

from . import Base  # 使用统一的 Base



class AuditLog(Base):
    """审计日志模型模型"""
    __tablename__ = 'audit_logs'


    __table_args__ = (
        Index('idx_audit_logs_user_action_time', 'user_id', 'action', 'created_at'),
        Index('idx_audit_logs_level_time', 'level', 'created_at'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
    )


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='日志 ID')

    user_id = Column(BigInteger, index=True, nullable=True, doc='用户 ID')

    user_name = Column(String(255), nullable=True, doc='用户名')

    action = Column(String(50), index=True, nullable=True, doc='操作类型')

    level = Column(String(20), index=True, nullable=True, doc='日志级别')

    resource_type = Column(String(100), index=True, nullable=True, doc='资源类型')

    resource_id = Column(String(100), index=True, nullable=True, doc='资源 ID')

    ip_address = Column(String(45), nullable=True, doc='IP 地址')

    user_agent = Column(Text, nullable=True, doc='用户代理')

    description = Column(Text, nullable=True, doc='操作描述')

    details = Column(Text, nullable=True, doc='详细信息（JSON格式）')

    created_at = Column(DateTime, doc='创建时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'action': self.action,
            'level': self.level,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'description': self.description,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AuditLog id={self.id}>'
