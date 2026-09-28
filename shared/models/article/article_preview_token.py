"""
SQLAlchemy 模型定义 - ArticlePreviewToken
手写模型（写法定向对齐代码生成器产物，并在 config/models.yaml 登记）

草稿预览**令牌**：为未发布文章生成临时预览链接。与 v2 的
``services/articles/draft_preview_service.py`` 相比，这里落到真表：

  - v2 用 ``data/preview_tokens.json`` 文件存储（重启/多 worker 会不一致），v3 用表；
  - v2 用自制 salted-SHA256 存密码，v3 复用项目的 Argon2（``password_hash`` 存 Argon2 串）；
  - 归属与级联显式声明：文章删除时令牌 ``ON DELETE CASCADE``，创建者删除时置 NULL。
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class ArticlePreviewToken(Base):
    """文章草稿预览令牌模型"""
    __tablename__ = 'article_preview_tokens'

    __table_args__ = (
        Index('idx_article_preview_tokens_article', 'article_id'),
        Index('idx_article_preview_tokens_expires', 'expires_at'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='令牌 ID')

    article_id = Column(
        BigInteger, ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, doc='文章 ID'
    )

    token = Column(String(64), unique=True, nullable=False, doc='预览令牌（URL 安全随机串）')

    password_hash = Column(String(255), nullable=True, doc='访问密码的 Argon2 哈希（为空表示无需密码）')

    max_views = Column(BigInteger, nullable=True, doc='最大访问次数（为空表示不限）')

    view_count = Column(BigInteger, nullable=False, default=0, doc='已访问次数')

    is_active = Column(
        Boolean, nullable=False, default=True, doc='是否有效（撤销或达到访问上限后置 false）'
    )

    expires_at = Column(DateTime, nullable=False, doc='过期时间')

    created_by = Column(
        BigInteger, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, doc='创建者用户 ID'
    )

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典（``password_hash`` 属敏感字段，默认排除）"""
        data = {
            'id': self.id,
            'article_id': self.article_id,
            'token': self.token,
            'max_views': self.max_views,
            'view_count': self.view_count,
            'is_active': self.is_active,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_by': self.created_by,
            'has_password': self.password_hash is not None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if not exclude_sensitive:
            data['password_hash'] = self.password_hash
        return data

    def __repr__(self):
        return f'<ArticlePreviewToken id={self.id} article_id={self.article_id} active={self.is_active}>'
