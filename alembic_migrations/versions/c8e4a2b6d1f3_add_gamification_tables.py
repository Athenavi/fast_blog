"""add gamification tables (points + badges)

Revision ID: c8e4a2b6d1f3
Revises: b3d7f1a5c8e2
Create Date: 2026-09-20

新增 T5-11 批次 12 的 **积分与勋章** 五张表：

  - ``user_points``           积分账户（一人一行）
  - ``points_transactions``   积分流水
  - ``points_rules``          积分规则（v2 是类内常量，这里改为入库可配）
  - ``badge_definitions``     勋章定义（v2 的 18 个内置徽章 → 种子数据）
  - ``user_badges``           用户已获勋章

唯一键走**命名 UniqueConstraint / unique Index**（与模型声明一致），不重复建同名对象。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c8e4a2b6d1f3"
down_revision = "b3d7f1a5c8e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------- 积分账户
    op.create_table(
        "user_points",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="账户 ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=True, comment="用户 ID"),
        sa.Column("balance", sa.Integer(), server_default="0", nullable=True, comment="当前可用积分"),
        sa.Column("total_earned", sa.Integer(), server_default="0", nullable=True, comment="累计获得"),
        sa.Column("total_spent", sa.Integer(), server_default="0", nullable=True, comment="累计消耗"),
        sa.Column("last_checkin_at", sa.DateTime(), nullable=True, comment="最后签到时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_user_points_user", "user_points", ["user_id"], unique=True)
    op.create_index("idx_user_points_balance", "user_points", ["balance"])

    # ---------------------------------------------------------------- 积分流水
    op.create_table(
        "points_transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="流水 ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=True, comment="用户 ID"),
        sa.Column("amount", sa.Integer(), nullable=True, comment="变动值"),
        sa.Column("balance_after", sa.Integer(), nullable=True, comment="变动后余额"),
        sa.Column("action", sa.String(length=50), nullable=True, comment="动作标识"),
        sa.Column("description", sa.String(length=255), nullable=True, comment="说明"),
        sa.Column("reference_id", sa.BigInteger(), nullable=True, comment="关联记录 ID"),
        sa.Column("reference_type", sa.String(length=50), nullable=True, comment="关联记录类型"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="发生时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_points_tx_user_created", "points_transactions", ["user_id", "created_at"])
    op.create_index("idx_points_tx_action", "points_transactions", ["action"])

    # ---------------------------------------------------------------- 积分规则
    op.create_table(
        "points_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="规则 ID"),
        sa.Column("action", sa.String(length=50), nullable=False, comment="动作标识（唯一）"),
        sa.Column("points", sa.Integer(), nullable=True, comment="积分值"),
        sa.Column("description", sa.String(length=255), nullable=True, comment="说明"),
        sa.Column("daily_limit", sa.Integer(), server_default="0", nullable=True, comment="每日上限"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_points_rules_action", "points_rules", ["action"], unique=True)

    # ---------------------------------------------------------------- 勋章定义
    op.create_table(
        "badge_definitions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="勋章 ID"),
        sa.Column("badge_key", sa.String(length=50), nullable=False, comment="勋章标识（唯一）"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="名称"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("points_reward", sa.Integer(), server_default="0", nullable=True),
        sa.Column("condition_type", sa.String(length=50), nullable=True),
        sa.Column("condition_value", sa.Integer(), server_default="0", nullable=True),
        sa.Column("is_manual", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_badge_definitions_key", "badge_definitions", ["badge_key"], unique=True)
    op.create_index("idx_badge_definitions_category", "badge_definitions", ["category"])

    # ---------------------------------------------------------------- 用户勋章
    op.create_table(
        "user_badges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="记录 ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=True, comment="用户 ID"),
        sa.Column("badge_key", sa.String(length=50), nullable=False, comment="勋章标识"),
        sa.Column("awarded_at", sa.DateTime(), nullable=True, comment="获得时间"),
        sa.Column("awarded_by", sa.BigInteger(), nullable=True, comment="手工授予的管理员 ID"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_user_badges_unique", "user_badges", ["user_id", "badge_key"], unique=True)
    op.create_index("idx_user_badges_badge", "user_badges", ["badge_key"])


def downgrade() -> None:
    op.drop_index("idx_user_badges_badge", table_name="user_badges")
    op.drop_index("idx_user_badges_unique", table_name="user_badges")
    op.drop_table("user_badges")

    op.drop_index("idx_badge_definitions_category", table_name="badge_definitions")
    op.drop_index("idx_badge_definitions_key", table_name="badge_definitions")
    op.drop_table("badge_definitions")

    op.drop_index("idx_points_rules_action", table_name="points_rules")
    op.drop_table("points_rules")

    op.drop_index("idx_points_tx_action", table_name="points_transactions")
    op.drop_index("idx_points_tx_user_created", table_name="points_transactions")
    op.drop_table("points_transactions")

    op.drop_index("idx_user_points_balance", table_name="user_points")
    op.drop_index("idx_user_points_user", table_name="user_points")
    op.drop_table("user_points")
