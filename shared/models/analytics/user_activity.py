"""
SQLAlchemy 模型定义 - UserActivity
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-06-13 23:12:16
"""

from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class UserActivity(Base):
    """用户活动模型模型"""
    __tablename__ = 'user_activities'
    # 手工补充的索引：活动流水表按时间/用户/类型查询，无索引会全表扫描。
    # （模型由生成器产出，若重新生成请同步 config/models.yaml 的 indexes 段。）
    __table_args__ = (
        Index('idx_user_activities_created_at', 'created_at'),
        Index('idx_user_activities_user_created', 'user', 'created_at'),
        Index('idx_user_activities_type_created', 'activity_type', 'created_at'),
    )

    site_id = Column(BigInteger, nullable=True, index=True, doc='所属站点 ID（多租户隔离键）')
    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='活动 ID')

    user = Column(BigInteger, ForeignKey('users.id'), doc='用户')


    activity_type = Column(String(100), nullable=True, doc='活动类型')

    target_type = Column(String(50), nullable=True, doc='目标类型')

    target_id = Column(BigInteger, doc='目标 ID')


    details = Column(String(255), nullable=True, doc='活动详情')

    ip_address = Column(String(45), nullable=True, doc='IP 地址')

    user_agent = Column(String(500), nullable=True, doc='用户代理')

    created_at = Column(DateTime, doc='活动时间')


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

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<UserActivity id={self.id}>'


