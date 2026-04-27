"""
SQLAlchemy 模型定义 - User
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Integer, String,
                        Text)

from . import Base  # 使用统一的 Base

# ============================================================================
# 自定义方法导入提示
# 以下导入是自定义方法可能需要的，如果不需要可以删除：
# - from datetime import datetime
# ============================================================================


class User(Base):
    """用户模型模型"""
    __tablename__ = 'users'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    username = Column(String(255), unique=True, nullable=True, doc='username')


    email = Column(String(255), nullable=True, doc='email')

    password = Column(String(255), nullable=True, doc='password')

    profile_picture = Column(String(255), nullable=True, doc='profile_picture')

    bio = Column(String(255), nullable=True, doc='bio')

    profile_private = Column(Boolean, default=False, doc='profile_private')

    vip_level = Column(BigInteger, default=0, doc='vip_level')

    vip_expires_at = Column(DateTime, nullable=True, doc='vip_expires_at')

    is_active = Column(Boolean, default=True, doc='is_active')

    is_superuser = Column(Boolean, default=False, doc='is_superuser')

    date_joined = Column(DateTime, doc='date_joined')

    last_login_at = Column(DateTime, nullable=True, doc='last_login_at')

    locale = Column(String(255), default='zh_CN', doc='locale')

    is_staff = Column(Boolean, default=False, doc='is_staff')

    last_login_ip = Column(String(255), nullable=True, doc='last_login_ip')

    register_ip = Column(String(255), nullable=True, doc='register_ip')

    is_2fa_enabled = Column(Boolean, default=False, doc='is_2fa_enabled')

    totp_secret = Column(String(255), nullable=True, doc='totp_secret')

    backup_codes = Column(String(255), nullable=True, doc='backup_codes')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'profile_picture': self.profile_picture,
            'bio': self.bio,
            'profile_private': self.profile_private,
            'vip_level': self.vip_level,
            'vip_expires_at': self.vip_expires_at.isoformat() if self.vip_expires_at else None,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'date_joined': self.date_joined.isoformat() if self.date_joined else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'locale': self.locale,
            'is_staff': self.is_staff,
            'is_2fa_enabled': self.is_2fa_enabled,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
                'password': self.password,
                'last_login_ip': self.last_login_ip,
                'register_ip': self.register_ip,
                'totp_secret': self.totp_secret,
                'backup_codes': self.backup_codes,
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<User id={self.id}>'

    def is_vip(self) -> bool:
        """
        判断是否为 VIP 用户

        Returns:
            bool: 是否为 VIP 用户
        """
        if not self.vip_level:
            return False

        # 检查 VIP 是否过期
        if self.vip_expires_at:
            try:
                # 如果 vip_expires_at 是字符串，尝试解析
                if isinstance(self.vip_expires_at, str):
                    expires = datetime.fromisoformat(self.vip_expires_at.replace('Z', '+00:00'))
                    return datetime.now(expires.tzinfo) < expires
                else:
                    # 如果是 datetime 对象
                    tzinfo = getattr(self.vip_expires_at, 'tzinfo', None)
                    return datetime.now(tzinfo) < self.vip_expires_at
            except Exception:
                # 如果解析失败，只检查 vip_level
                return self.vip_level > 0

        return self.vip_level > 0


    def get_display_name(self) -> str:
        """
        获取显示名称

        Returns:
            str: 显示名称（优先返回 username）
        """
        if hasattr(self, 'username'):
            return self.username
        if hasattr(self, 'name'):
            return self.name
        return f"User_{self.id}"
