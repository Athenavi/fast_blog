"""
SQLAlchemy 模型定义 - Order
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-05-06 17:19:47
"""


from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, Float, Numeric, ForeignKey

from . import Base  # 使用统一的 Base

from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, DateTime, Float, Numeric, ForeignKey, Index

class Order(Base):
    """订单模型模型"""
    __tablename__ = 'orders'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    order_number = Column(String(50), unique=True, nullable=True, doc='order_number')


    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user_id')


    status = Column(String(50), default='pending', doc='status')

    total_amount = Column(Numeric(10, 2), doc='total_amount')

    shipping_amount = Column(Numeric(10, 2), default=0, doc='shipping_amount')

    discount_amount = Column(Numeric(10, 2), default=0, doc='discount_amount')

    payment_method = Column(String(50), nullable=True, doc='payment_method')

    payment_status = Column(String(50), default='pending', doc='payment_status')

    transaction_id = Column(String(255), nullable=True, doc='transaction_id')

    shipping_address = Column(String(255), nullable=True, doc='shipping_address')

    billing_address = Column(String(255), nullable=True, doc='billing_address')

    notes = Column(Text, nullable=True, doc='notes')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')

    paid_at = Column(DateTime, nullable=True, doc='paid_at')

    shipped_at = Column(DateTime, nullable=True, doc='shipped_at')

    delivered_at = Column(DateTime, nullable=True, doc='delivered_at')

    __table_args__ = (

        Index('idx_orders_order_number', 'order_number', unique=True),
        Index('idx_orders_user', 'user_id'),
        Index('idx_orders_status', 'status'),
        Index('idx_orders_payment_status', 'payment_status'),
        Index('idx_orders_created', 'created_at'),
        Index('idx_orders_user_status_created', 'user_id', 'status', 'created_at'),
        Index('idx_orders_status_payment_created', 'status', 'payment_status', 'created_at'),
        Index('idx_orders_payment_transaction', 'transaction_id'),
    )

    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'order_number': self.order_number,
            'user_id': self.user_id,
            'status': self.status,
            'total_amount': self.total_amount,
            'shipping_amount': self.shipping_amount,
            'discount_amount': self.discount_amount,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'transaction_id': self.transaction_id,
            'shipping_address': self.shipping_address,
            'billing_address': self.billing_address,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Order id={self.id}>'
