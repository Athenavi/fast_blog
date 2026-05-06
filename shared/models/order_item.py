"""
SQLAlchemy 模型定义 - OrderItem
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-05-06 17:36:26
"""

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Numeric, ForeignKey, Index

from . import Base  # 使用统一的 Base


class OrderItem(Base):
    """订单项模型模型"""
    __tablename__ = 'order_items'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    order_id = Column(BigInteger, ForeignKey('orders.id'), nullable=False, doc='order_id')


    product_id = Column(BigInteger, ForeignKey('products.id'), nullable=False, doc='product_id')


    product_name = Column(String(255), nullable=True, doc='product_name')


    quantity = Column(Integer, doc='quantity')


    price = Column(Numeric(10, 2), doc='price')


    total = Column(Numeric(10, 2), doc='total')


    created_at = Column(DateTime, doc='created_at')


    __table_args__ = (

    Index('idx_order_items_order', 'order_id'),
        Index('idx_order_items_product', 'product_id'),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'price': self.price,
            'total': self.total,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<OrderItem id={self.id}>'
