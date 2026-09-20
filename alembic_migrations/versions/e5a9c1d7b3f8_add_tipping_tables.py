"""add tipping tables (tips + withdrawals)

Revision ID: e5a9c1d7b3f8
Revises: d1f6b8c3a9e7
Create Date: 2026-09-20

新增 T5-11 批次 14 的**打赏与提现**两张表：

  - ``tips``             打赏记录（金额单位：**分**；真钱走 payment-gateway 插件）
  - ``tip_withdrawals``  打赏收益提现申请（pending → approved / rejected → paid）

v2 没有任何对应表（内存单例，且引用了不存在的列），所以这是**从零建**。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5a9c1d7b3f8"
down_revision = "d1f6b8c3a9e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------- 打赏记录
    op.create_table(
        "tips",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="打赏 ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="打赏者 ID"),
        sa.Column("author_id", sa.BigInteger(), nullable=False, comment="被打赏者 ID"),
        sa.Column("article_id", sa.BigInteger(), nullable=True, comment="被打赏文章 ID"),
        sa.Column("amount", sa.Integer(), nullable=False, comment="打赏金额（分）"),
        sa.Column("message", sa.String(length=255), nullable=True, comment="留言"),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=True, comment="状态"),
        sa.Column("order_no", sa.String(length=64), nullable=False, comment="本地订单号"),
        sa.Column("provider", sa.String(length=32), nullable=True, comment="支付渠道"),
        sa.Column("transaction_id", sa.String(length=128), nullable=True, comment="支付网关交易号"),
        sa.Column("paid_at", sa.DateTime(), nullable=True, comment="支付时间"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_tips_order_no", "tips", ["order_no"], unique=True)
    op.create_index("idx_tips_author_status", "tips", ["author_id", "status"])
    op.create_index("idx_tips_user_created", "tips", ["user_id", "created_at"])

    # ---------------------------------------------------------------- 提现申请
    op.create_table(
        "tip_withdrawals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="提现 ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="申请人 ID"),
        sa.Column("amount", sa.Integer(), nullable=False, comment="申请金额（分）"),
        sa.Column("fee", sa.Integer(), server_default="0", nullable=True, comment="手续费（分）"),
        sa.Column("actual_amount", sa.Integer(), server_default="0", nullable=True, comment="实际到账（分）"),
        sa.Column("method", sa.String(length=32), nullable=True, comment="提现方式"),
        sa.Column("account", sa.String(length=255), nullable=True, comment="收款账号（敏感）"),
        sa.Column("account_name", sa.String(length=100), nullable=True, comment="收款人姓名"),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=True, comment="状态"),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="审核时间"),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=True, comment="审核人 ID"),
        sa.Column("review_comment", sa.String(length=500), nullable=True, comment="审核意见"),
        sa.Column("paid_at", sa.DateTime(), nullable=True, comment="打款时间"),
        sa.Column("transaction_id", sa.String(length=128), nullable=True, comment="打款流水号"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_tip_withdrawals_user_status", "tip_withdrawals", ["user_id", "status"])
    op.create_index("idx_tip_withdrawals_status", "tip_withdrawals", ["status"])


def downgrade() -> None:
    op.drop_index("idx_tip_withdrawals_status", table_name="tip_withdrawals")
    op.drop_index("idx_tip_withdrawals_user_status", table_name="tip_withdrawals")
    op.drop_table("tip_withdrawals")

    op.drop_index("idx_tips_user_created", table_name="tips")
    op.drop_index("idx_tips_author_status", table_name="tips")
    op.drop_index("idx_tips_order_no", table_name="tips")
    op.drop_table("tips")
