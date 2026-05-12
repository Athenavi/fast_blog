"""
SQLAlchemy 模型定义 - OrderItem
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-05-12 11:11:20
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Numeric, ForeignKey, Index

from . import Base  # 使用统一的 Base


class OrderItem(Base):
    """订单项模型模型"""
    __tablename__ = 'order_items'


    __table_args__ = (
        Index('idx_order_items_order', 'order_id'),
        Index('idx_order_items_product', 'product_id'),
    )


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='订单项 ID')

    order_id = Column(BigInteger, ForeignKey('orders.id'), doc='订单ID')


    product_id = Column(BigInteger, ForeignKey('products.id'), doc='商品ID')


    product_name = Column(String(255), nullable=True, doc='商品名称(快照)')

    quantity = Column(Integer, doc='数量')


    price = Column(Numeric(10, 2), doc='单价')


    total = Column(Numeric(10, 2), doc='小计')


    created_at = Column(DateTime, doc='创建时间')


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

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<OrderItem id={self.id}>'


