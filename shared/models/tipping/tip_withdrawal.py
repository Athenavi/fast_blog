"""
SQLAlchemy 模型定义 - TipWithdrawal
手写模型（T5-11 批次 14），写法对齐代码生成器产物。

打赏收益**提现申请**。金额单位是**分**。

状态机：``pending``（待审）→ ``approved``（已批准）/ ``rejected``（已驳回）；
``approved`` → ``paid``（已打款，人工转账后由管理员标记并填流水号）。

**不做自动打款**：真实打款需要支付渠道的"转账/代付"产品与商户资质，
插件层只有"收款"能力（``execute:custom:payment``）。所以这一环走人工，
但状态、金额、手续费、到账额、流水号都如实入库，可对账。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class TipWithdrawal(Base):
    """打赏提现申请模型"""
    __tablename__ = 'tip_withdrawals'

    __table_args__ = (
        Index('idx_tip_withdrawals_user_status', 'user_id', 'status'),
        Index('idx_tip_withdrawals_status', 'status'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='提现 ID')

    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='申请人 ID')

    amount = Column(Integer, nullable=False, doc='申请金额（单位：分）')

    fee = Column(Integer, default=0, doc='手续费（分）')

    actual_amount = Column(Integer, default=0, doc='实际到账（分）')

    method = Column(String(32), doc='提现方式：alipay / wechat / bank')

    account = Column(String(255), doc='收款账号')

    account_name = Column(String(100), doc='收款人姓名')

    status = Column(String(20), default='pending', doc='状态：pending / approved / rejected / paid')

    reviewed_at = Column(DateTime, nullable=True, doc='审核时间')

    reviewer_id = Column(BigInteger, nullable=True, doc='审核人 ID')

    review_comment = Column(String(500), nullable=True, doc='审核意见')

    paid_at = Column(DateTime, nullable=True, doc='打款时间')

    transaction_id = Column(String(128), nullable=True, doc='打款流水号')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（收款账号默认排除）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'fee': self.fee,
            'actual_amount': self.actual_amount,
            'method': self.method,
            'account_name': self.account_name,
            'status': self.status,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewer_id': self.reviewer_id,
            'review_comment': self.review_comment,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'transaction_id': self.transaction_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
                'account': self.account,
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<TipWithdrawal id={self.id} amount={self.amount} status={self.status}>'
