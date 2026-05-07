"""
SQLAlchemy 模型定义 - CartItem
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-05-07 16:38:48
"""

from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, Float, Numeric, ForeignKey

from . import Base  # 使用统一的 Base

from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, Float, Numeric, ForeignKey, Index

class CartItem(Base):
    """购物车项模型模型"""
    __tablename__ = 'cart_items'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    cart_id = Column(BigInteger, ForeignKey('carts.id'), nullable=False, doc='cart_id')


    product_id = Column(BigInteger, ForeignKey('products.id'), nullable=False, doc='product_id')


    quantity = Column(Integer, default=1, doc='quantity')


    price = Column(Numeric(10, 2), doc='price')


    created_at = Column(DateTime, doc='created_at')


    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

        Index('idx_cart_items_cart', 'cart_id'),
        Index('idx_cart_items_product', 'product_id'),
        Index('idx_cart_items_unique', 'cart_id', 'product_id', unique=True),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'cart_id': self.cart_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'price': self.price,
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
        return f'<CartItem id={self.id}>'
