"""
SQLAlchemy 模型定义 - ThemePackage
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-05-25 10:58:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Index

from . import Base  # 使用统一的 Base



class ThemePackage(Base):
    """主题包管理模型模型"""
    __tablename__ = 'theme_packages'


    __table_args__ = (
        Index('idx_theme_packages_slug', 'slug', unique=True),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='主题 ID')

    name = Column(String(100), nullable=True, doc='主题显示名称')

    slug = Column(String(100), unique=True, nullable=True, doc='主题唯一标识')

    version = Column(String(20), nullable=True, doc='版本号')

    author = Column(String(100), nullable=True, doc='作者')

    config_data = Column(Text, nullable=False, doc='主题配置 (JSON 格式)')

    is_active = Column(Boolean, default=False, doc='是否当前启用')

    created_at = Column(DateTime, doc='创建时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'version': self.version,
            'author': self.author,
            'config_data': self.config_data,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<ThemePackage id={self.id}>'
