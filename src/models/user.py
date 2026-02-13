from datetime import datetime, timezone
from typing import List

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship

from src.utils.security.password_validator import verify_password
from . import Base  # 使用统一的Base


class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = 'users'

    # 定义主键ID字段
    id = Column(Integer, primary_key=True)

    # 额外的自定义字段（除了继承的字段）
    username = Column(String(255), nullable=False, unique=True, doc='用户名')
    created_at = Column(DateTime, default=lambda: datetime.now())  # 移除timezone.utc以避免时区冲突
    updated_at = Column(DateTime, default=lambda: datetime.now(),  # 移除timezone.utc以避免时区冲突
                        onupdate=lambda: datetime.now())
    profile_picture = Column(String(255), doc='头像')
    bio = Column(Text, doc='个人简介')
    register_ip = Column(String(45), nullable=False, doc='注册IP')
    is_2fa_enabled = Column(Boolean, default=False, doc='是否启用双因子认证')
    totp_secret = Column(String(32), doc='双因子认证密钥')
    backup_codes = Column(Text, doc='备用验证码')
    profile_private = Column(Boolean, default=False, doc='是否私密资料')
    vip_level = Column(Integer, default=0)  # VIP等级，0表示非VIP
    vip_expires_at = Column(DateTime)  # VIP过期时间
    last_login_at = Column(DateTime, doc='上次登录时间')
    last_login_ip = Column(String(45), doc='上次登录IP')
    locale = Column(String(10), default='zh_CN', doc='语言')

    # 关系定义
    media = relationship('Media', back_populates='user', lazy=True, cascade='all, delete',
                         primaryjoin="Media.user_id == foreign(User.id)",
                         overlaps="author,recipient,subscriber,user,user")

    articles = relationship('Article', back_populates='author', lazy='select', cascade='all, delete',
                            primaryjoin="Article.user_id == foreign(User.id)",
                            overlaps="media,recipient,subscriber,user,user")
    notifications = relationship('Notification', back_populates='recipient', lazy='select',
                                 cascade='delete',
                                 primaryjoin="Notification.recipient_id == foreign(User.id)",
                                 overlaps="articles,author,media,subscriber,user,user")
    custom_fields = relationship('CustomField', back_populates='user', lazy='select', cascade='all, delete',
                                 primaryjoin="CustomField.user_id == foreign(User.id)",
                                 overlaps="articles,author,media,notifications,recipient,subscriber,user,user")
    email_subscription = relationship('EmailSubscription', back_populates='user', uselist=False,
                                      cascade='all, delete',
                                      primaryjoin="EmailSubscription.user_id == foreign(User.id)",
                                      overlaps="articles,author,custom_fields,media,notifications,recipient,subscriber,user,user")
    category_subscriptions = relationship('CategorySubscription', back_populates='subscriber', lazy='select',
                                          cascade='all, delete',
                                          primaryjoin="CategorySubscription.subscriber_id == foreign(User.id)",
                                          overlaps="articles,author,custom_fields,email_subscription,media,notifications,recipient,user,user")
    vip_subscriptions = relationship('VIPSubscription', back_populates='user',
                                     lazy='select', cascade='all, delete',
                                     primaryjoin="VIPSubscription.user_id == foreign(User.id)",
                                     overlaps="articles,author,category_subscriptions,custom_fields,email_subscription,media,notifications,recipient,subscriber,user,user")

    # 用户活动关系
    activities = relationship('UserActivity', back_populates='user', lazy='select', cascade='all, delete', uselist=False,
                              overlaps="articles,author,category_subscriptions,custom_fields,email_subscription,media,notifications,recipient,subscriber,user,user")

    # 角色关系
    roles = relationship('Role', secondary='user_roles', primaryjoin="User.id == user_roles.c.user_id",
                         secondaryjoin="Role.id == user_roles.c.role_id", back_populates='users', lazy='select',
                         overlaps="user_roles")

    # 用户角色关联关系
    user_roles = relationship('UserRole', back_populates='user',
                              overlaps="roles,user,role_permissions,users,permissions")

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'profile_picture': self.profile_picture,
            'bio': self.bio,
            'vip_level': self.vip_level or 0,
            'is_vip': self.is_vip() or False,
            'vip_expires_at': self.vip_expires_at.isoformat() if self.vip_expires_at else None,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'is_verified': self.is_verified
        }

    def is_vip(self) -> bool:
        """检查用户是否为VIP"""
        if self.vip_level and self.vip_level > 0:
            if self.vip_expires_at and self.vip_expires_at > datetime.now():
                return True
        return False

    def has_role(self, role_name: str) -> bool:
        """检查用户是否拥有指定角色"""
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission_code: str) -> bool:
        """检查用户是否拥有指定权限"""
        for role in self.roles:
            if any(perm.code == permission_code for perm in role.permissions):
                return True
        return False

    def get_all_permissions(self) -> List[str]:
        """获取用户所有权限代码"""
        permissions = set()
        for role in self.roles:
            for perm in role.permissions:
                permissions.add(perm.code)
        return list(permissions)

    def check_password(self, password: str) -> bool:
        """检查提供的密码是否与用户哈希密码匹配"""
        return verify_password(password, self.hashed_password)

    def set_password(self, password: str):
        """设置用户密码，使用哈希算法加密"""
        from src.extensions import pwd_context
        try:
            self.hashed_password = pwd_context.hash(password)
        except AttributeError:
            # 处理pwd_context兼容性问题
            import bcrypt
            self.hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


class CustomField(Base):
    __tablename__ = 'custom_fields'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    field_name = Column(String(100), nullable=False)
    field_value = Column(Text, nullable=False, doc='自定义字段值')

    # 关系定义
    user = relationship('User', back_populates='custom_fields', primaryjoin="CustomField.user_id == foreign(User.id)",
                        overlaps="articles,author,category_subscriptions,email_subscription,media,notifications,user,vip_subscriptions")

    __table_args__ = (
        # 为user_id创建索引
        # 注意：这里需要根据SQLAlchemy的语法调整
    )


class EmailSubscription(Base):
    __tablename__ = 'email_subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    subscribed = Column(Boolean, default=True, nullable=False, doc='是否订阅邮件')
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # 关系定义
    user = relationship('User', back_populates='email_subscription',
                        primaryjoin="EmailSubscription.user_id == foreign(User.id)",
                        overlaps="articles,author,category_subscriptions,custom_fields,media,notifications,recipient,subscriber,user,vip_subscriptions")

    __table_args__ = (
        # 为user_id创建索引
        # 注意：这里需要根据SQLAlchemy的语法调整
    )