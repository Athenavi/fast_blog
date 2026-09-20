"""
SQLAlchemy 模型定义 - Tip
手写模型（T5-11 批次 14），写法对齐代码生成器产物。

打赏**记录**。金额单位是**分**（与支付插件一致），不是元。

> v2 的 `services/advanced_features/tipping_system.py` 是内存单例，而且它引用了不存在的列
> ``Article.user_id``（真实列名是 ``user``）—— 那个实现连查询都跑不起来。
>
> 真钱走的链路：``TipService.create`` 调支付插件下单 → 回调经 ``PaymentFlowService`` 验签
> → 命中本表 ``order_no`` 后置为 ``paid``。**没有真实回调就不算打赏成功**。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class Tip(Base):
    """打赏记录模型"""
    __tablename__ = 'tips'

    __table_args__ = (
        Index('idx_tips_order_no', 'order_no', unique=True),
        Index('idx_tips_author_status', 'author_id', 'status'),
        Index('idx_tips_user_created', 'user_id', 'created_at'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='打赏 ID')

    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='打赏者 ID')

    author_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='被打赏者 ID')

    article_id = Column(BigInteger, nullable=True, doc='被打赏文章 ID（直接打赏作者时为空）')

    amount = Column(Integer, nullable=False, doc='打赏金额（单位：分）')

    message = Column(String(255), nullable=True, doc='留言')

    status = Column(String(20), default='pending', doc='状态：pending / paid / failed / refunded')

    order_no = Column(String(64), nullable=False, doc='本地订单号（唯一）')

    provider = Column(String(32), nullable=True, doc='支付渠道')

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
            'author_id': self.author_id,
            'article_id': self.article_id,
            'amount': self.amount,
            'message': self.message,
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
        return f'<Tip id={self.id} amount={self.amount} status={self.status}>'
