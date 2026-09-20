"""
SQLAlchemy 模型定义 - VipPaymentOrder
手写模型（2026-09-20 批次 16：VIP 自助开通），写法对齐代码生成器产物。

**VIP 开通的支付订单**：`POST /api/v3/mobile/vip/create-payment` 先落一条 ``pending`` 订单，
再去 payment-gateway 插件下单；网关回调经 ``PaymentFlowService`` **验签通过**后才置为
``paid``，并调用 ``MembershipService.create_subscription`` 真正开通订阅。
**没有验签通过的回调就永远停在 pending**（不可能"假装已开通"）。

金额单位是**元**（与 ``vip_plans.price`` 的 ``Numeric(10, 2)`` 一致），不是 commerce 域的"分"
—— 套餐价格本来就是元，两处都用元可以省掉换算与单位错误。

为什么不复用 ``payment_transactions``：那张表属财务模块（人工记账口径），而这里是**订阅开通的凭据**；
为什么不把待支付订单写进 ``vip_subscriptions``：那会让未付款的订单污染订阅历史与管理端订阅列表。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Numeric, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class VipPaymentOrder(Base):
    """VIP 支付订单模型"""
    __tablename__ = 'vip_payment_orders'

    __table_args__ = (
        Index('idx_vip_payment_orders_order_no', 'order_no', unique=True),
        Index('idx_vip_payment_orders_user_status', 'user_id', 'status'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='订单 ID')

    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='下单用户 ID')

    plan_id = Column(BigInteger, ForeignKey('vip_plans.id'), nullable=False, doc='套餐 ID')

    amount = Column(Numeric(10, 2), nullable=False, doc='应付金额（单位：元）')

    status = Column(String(20), default='pending', doc='状态：pending / paid / failed')

    order_no = Column(String(64), nullable=False, doc='本地订单号（唯一）')

    provider = Column(String(32), nullable=True, doc='支付渠道（alipay/wechat/stripe…）')

    transaction_id = Column(String(128), nullable=True, doc='支付网关交易号')

    paid_at = Column(DateTime, nullable=True, doc='支付时间')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'amount': float(self.amount) if self.amount is not None else None,
            'status': self.status,
            'order_no': self.order_no,
            'provider': self.provider,
            'transaction_id': self.transaction_id,
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
        return f'<VipPaymentOrder id={self.id} order_no={self.order_no}>'
