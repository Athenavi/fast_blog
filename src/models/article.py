from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, BigInteger, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from . import Base  # 使用统一的Base


class Article(Base):
    __tablename__ = 'articles'
    article_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    user_id = Column(Integer, nullable=False)
    hidden = Column(Boolean, default=False, nullable=False)
    views = Column(BigInteger, default=0, nullable=False)
    likes = Column(BigInteger, default=0, nullable=False)
    status = Column(Integer, default=0, nullable=False)
    cover_image = Column(String(255))
    category_id = Column(Integer, nullable=True)
    excerpt = Column(Text)
    is_featured = Column(Boolean, default=False)
    tags = Column(String(255), nullable=False)
    article_ad = Column(Text)
    is_vip_only = Column(Boolean, default=False)
    required_vip_level = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(),
                        onupdate=lambda: datetime.now())

    # Relationship with author
    author = relationship('User', back_populates='articles', primaryjoin="Article.user_id == foreign(User.id)")
    # Relationship with category
    category = relationship('Category', back_populates='articles', primaryjoin="Article.category_id == foreign(Category.id)",
                          overlaps="subscriptions")

    def to_dict(self):
        return {
            'id': self.article_id,
            'title': self.title,
            'slug': self.slug,
            'user_id': self.user_id,
            'hidden': self.hidden,
            'views': self.views,
            'likes': self.likes,
            'status': self.status,
            'cover_image': self.cover_image,
            'category_id': self.category_id,
            'excerpt': self.excerpt,
            'is_featured': self.is_featured,
            'tags': self.tags,
            'article_ad': self.article_ad,
            'is_vip_only': self.is_vip_only,
            'required_vip_level': self.required_vip_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ArticleContent(Base):
    __tablename__ = 'article_content'
    aid = Column(Integer, primary_key=True)
    passwd = Column(String(128))
    content = Column(Text)
    updated_at = Column(DateTime, default=lambda: datetime.now(),
                        onupdate=lambda: datetime.now())
    language_code = Column(String(10), default='zh-CN', nullable=False)

    # Relationship with article
    article = relationship('Article', primaryjoin="ArticleContent.aid == foreign(Article.article_id)", overlaps="article")


class ArticleI18n(Base):
    __tablename__ = 'article_i18n'
    i18n_id = Column(Integer, primary_key=True)
    article_id = Column(Integer, nullable=False)
    language_id = Column(String(10), nullable=False)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    excerpt = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(),
                        onupdate=lambda: datetime.now())

    # Relationship with article
    article = relationship('Article', primaryjoin="ArticleI18n.article_id == foreign(Article.article_id)", overlaps="article")

    __table_args__ = (
        UniqueConstraint('article_id', 'language_id', name='uq_article_language'),
    )


class ArticleLike(Base):
    """
    文章点赞记录表，用于记录用户对文章的点赞情况，防止重复点赞
    """
    __tablename__ = 'article_likes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    article_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now())

    # Relationships
    user = relationship('User', primaryjoin="ArticleLike.user_id == foreign(User.id)",
                        overlaps="articles,author,media,notifications,recipient,subscriber,user,vip_subscriptions")
    article = relationship('Article', primaryjoin="ArticleLike.article_id == foreign(Article.article_id)",
                          overlaps="articles,author,content,i18n")

    # 确保一个用户对一篇文章只能点赞一次
    __table_args__ = (
        UniqueConstraint('user_id', 'article_id', name='uq_user_article_like'),
    )

    def __repr__(self):
        return f'<ArticleLike user_id={self.user_id} article_id={self.article_id}>'