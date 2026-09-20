"""
SQLAlchemy 模型定义 - UserFollow
手写模型（v3 mobile/follow 批次），写法对齐代码生成器产物。

前台关注关系（fans）。命名跟随既有的 ``user_blocks``（``blocker`` / ``blocked_user``）：
这里是 ``follower``（关注者）/ ``following``（被关注者），配对唯一。

> v2 的 6 个关注端点读写的是**模块级内存字典**（进程重启即丢，注释自承"后续应迁移到数据库表"），
> 且仓库里从来没有 follow 表 —— 这是本批次新建的关系表。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, UniqueConstraint

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class UserFollow(Base):
    """用户关注关系模型"""
    __tablename__ = 'user_follows'

    __table_args__ = (
        # 命名唯一约束（与迁移口径一致：不重复创建同名 Index）
        UniqueConstraint('follower', 'following', name='idx_user_follows_unique'),
        Index('idx_user_follows_following', 'following'),
        Index('idx_user_follows_created', 'created_at'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='关注 ID')

    follower = Column(BigInteger, ForeignKey('users.id'), doc='关注者（发起方）')

    following = Column(BigInteger, ForeignKey('users.id'), doc='被关注者（目标）')

    created_at = Column(DateTime, doc='关注时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'follower': self.follower,
            'following': self.following,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<UserFollow id={self.id}>'
