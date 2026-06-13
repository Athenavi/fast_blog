"""
SQLAlchemy 模型定义 - CustomPostContent
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-06-13 22:45:57
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Index

from shared.models import Base  # 使用统一的 Base（跨子包引用）



class CustomPostContent(Base):
    """自定义文章类型内容模型模型"""
    __tablename__ = 'custom_post_contents'


    __table_args__ = (
        Index('idx_cpc_post_type', 'post_type_id'),
        Index('idx_cpc_slug', 'slug', unique=True),
        Index('idx_cpc_author', 'author_id'),
        Index('idx_cpc_status', 'status'),
        Index('idx_cpc_created', 'created_at'),
    )


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='内容 ID')

    post_type_id = Column(BigInteger, ForeignKey('custom_post_types.id'), doc='文章类型 ID')


    title = Column(String(255), nullable=True, doc='标题')

    slug = Column(String(100), unique=True, nullable=True, doc='内容标识')

    content = Column(Text, nullable=True, doc='内容（HTML 或 JSON 块数据）')


    excerpt = Column(String(500), nullable=True, doc='摘要')

    meta = Column(Text, nullable=True, doc='元数据（JSON 格式）')


    author_id = Column(BigInteger, ForeignKey('users.id'), doc='作者 ID')


    status = Column(Integer, default=0, doc='状态（0: 草稿, 1: 已发布）')


    is_featured = Column(Boolean, default=False, doc='是否精选')


    password = Column(String(255), nullable=True, doc='访问密码')

    published_at = Column(DateTime, nullable=True, doc='发布时间')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'post_type_id': self.post_type_id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'excerpt': self.excerpt,
            'meta': self.meta,
            'author_id': self.author_id,
            'status': self.status,
            'is_featured': self.is_featured,
            'password': self.password,
            'published_at': self.published_at.isoformat() if self.published_at else None,
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
        return f'<CustomPostContent id={self.id}>'


