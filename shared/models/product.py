"""
SQLAlchemy 模型定义 - Product
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-05-07 16:38:48
"""

from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, Float, Numeric, ForeignKey

from . import Base  # 使用统一的 Base

from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, Float, Numeric, ForeignKey, Index

class Product(Base):
    """商品模型模型"""
    __tablename__ = 'products'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    name = Column(String(255), nullable=True, doc='name')


    slug = Column(String(255), unique=True, nullable=True, doc='slug')


    description = Column(Text, nullable=True, doc='description')


    price = Column(Numeric(10, 2), doc='price')


    original_price = Column(Numeric(10, 2), nullable=True, doc='original_price')


    stock = Column(Integer, default=0, doc='stock')


    sku = Column(String(100), index=True, nullable=True, doc='sku')


    images = Column(Text, nullable=True, doc='images')


    category_id = Column(BigInteger, ForeignKey('categories.id'), nullable=True, doc='category_id')


    is_active = Column(Boolean, default=True, doc='is_active')


    is_featured = Column(Boolean, default=False, doc='is_featured')


    weight = Column(Numeric(10, 2), nullable=True, doc='weight')


    dimensions = Column(Text, nullable=True, doc='dimensions')


    attributes = Column(Text, nullable=True, doc='attributes')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')

    __table_args__ = (

        Index('idx_products_slug', 'slug', unique=True),
        Index('idx_products_category', 'category_id'),
        Index('idx_products_is_active', 'is_active'),
        Index('idx_products_sku', 'sku'),
    )

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'price': self.price,
            'original_price': self.original_price,
            'stock': self.stock,
            'sku': self.sku,
            'images': self.images,
            'category_id': self.category_id,
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'weight': self.weight,
            'dimensions': self.dimensions,
            'attributes': self.attributes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Product id={self.id}>'
