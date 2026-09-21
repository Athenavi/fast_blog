"""
SQLAlchemy 模型定义 - PublishChannel
手写模型（2026-09-21 批次 18：多平台发布底座），写法对齐代码生成器产物。

**第三方发布渠道**：一条记录 = 一个"往哪儿发"的目标（一个平台账号 / 一个自建网关）。
凭据（app_id / app_secret / access_token 等）由 service 层用 AES-256-GCM 加密后写入
``credentials_encrypted``（与 ``ops/cdn``、``ai/config`` 同一套加解密约定），
**永不回传**：出参只有 ``has_credentials``。

``platform`` 是适配器注册表（``modules/content/third_party_publish/adapters.py``）的 key。
适配器**分期实现**：底座只保证"平台有适配器才可能成功"，未注册的平台执行时**如实失败**，
不会假装发布成功。
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, String, Text

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class PublishChannel(Base):
    """第三方发布渠道模型"""
    __tablename__ = 'publish_channels'

    __table_args__ = (
        Index('idx_publish_channels_platform_name', 'platform', 'name', unique=True),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='渠道 ID')

    name = Column(String(100), nullable=False, doc='渠道名（如「我的公众号」）')

    platform = Column(String(32), nullable=False, doc='平台标识（适配器注册表的 key）')

    endpoint = Column(String(255), nullable=True, doc='平台 API 基址覆盖（自建网关用）')

    credentials_encrypted = Column(
        Text, nullable=True, doc='凭据（JSON 经 AES-256-GCM 加密；永不回传）'
    )

    is_active = Column(Boolean, default=True, doc='是否启用')

    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='创建人 ID')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'platform': self.platform,
            'endpoint': self.endpoint,
            'is_active': bool(self.is_active),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
                'credentials_encrypted': self.credentials_encrypted,
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<PublishChannel id={self.id} platform={self.platform} name={self.name}>'
