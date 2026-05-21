"""
SQLAlchemy 模型定义 - Order
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-05-21 08:51:05
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Numeric, ForeignKey, Index

from . import Base  # 使用统一的 Base



class Order(Base):
    """订单模型模型"""
    __tablename__ = 'orders'


    __table_args__ = (
        Index('idx_order_user', 'user'),
        Index('idx_order_number', 'order_number', unique=True),
        Index('idx_order_status', 'status'),
        Index('idx_order_created', 'created_at'),
    )


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='订单 ID')

    user = Column(BigInteger, ForeignKey('users.id'), doc='用户')

    order_number = Column(String(50), unique=True, nullable=True, doc='订单编号')

    status = Column(String(20), default='pending', doc='订单状态')

    total_amount = Column(Numeric(10, 2), doc='总金额')

    currency = Column(String(3), default='USD', doc='货币类型')

    tax_amount = Column(Numeric(10, 2), default=0, doc='税额')

    shipping_address = Column(Text, nullable=True, doc='收货地址 (JSON格式)')

    billing_address = Column(Text, nullable=True, doc='账单地址 (JSON格式)')


    notes = Column(Text, nullable=True, doc='订单备注')

    payment_gateway = Column(BigInteger, ForeignKey('payment_gateways.id'), nullable=True, doc='支付网关')

    paid_at = Column(DateTime, nullable=True, doc='支付完成时间')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user': self.user,
            'order_number': self.order_number,
            'status': self.status,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'tax_amount': self.tax_amount,
            'shipping_address': self.shipping_address,
            'billing_address': self.billing_address,
            'notes': self.notes,
            'payment_gateway': self.payment_gateway,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
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
        return f'<Order id={self.id}>'


