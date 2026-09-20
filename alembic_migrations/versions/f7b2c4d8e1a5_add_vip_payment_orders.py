"""add vip payment orders

Revision ID: f7b2c4d8e1a5
Revises: e5a9c1d7b3f8
Create Date: 2026-09-20

新增 VIP 自助开通的**支付订单**表（批次 16）：

  - ``vip_payment_orders``  下单 → 支付插件 → 验签回调 → 才置 ``paid`` 并开通订阅

金额单位是**元**（与 ``vip_plans.price`` 的 ``NUMERIC(10, 2)`` 一致），不是 commerce 域的"分"。
待支付订单**不写** ``vip_subscriptions``，避免污染订阅历史与管理端列表。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f7b2c4d8e1a5"
down_revision = "e5a9c1d7b3f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vip_payment_orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="订单 ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="下单用户 ID"),
        sa.Column("plan_id", sa.BigInteger(), nullable=False, comment="套餐 ID"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, comment="应付金额（元）"),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=True, comment="状态"),
        sa.Column("order_no", sa.String(length=64), nullable=False, comment="本地订单号"),
        sa.Column("provider", sa.String(length=32), nullable=True, comment="支付渠道"),
        sa.Column("transaction_id", sa.String(length=128), nullable=True, comment="支付网关交易号"),
        sa.Column("paid_at", sa.DateTime(), nullable=True, comment="支付时间"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["vip_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_vip_payment_orders_order_no", "vip_payment_orders", ["order_no"], unique=True
    )
    op.create_index(
        "idx_vip_payment_orders_user_status", "vip_payment_orders", ["user_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("idx_vip_payment_orders_user_status", table_name="vip_payment_orders")
    op.drop_index("idx_vip_payment_orders_order_no", table_name="vip_payment_orders")
    op.drop_table("vip_payment_orders")
