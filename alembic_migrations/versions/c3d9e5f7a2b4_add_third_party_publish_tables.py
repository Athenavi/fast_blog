"""add third party publish tables

Revision ID: c3d9e5f7a2b4
Revises: b8e6f2a4c9d1
Create Date: 2026-09-21

新增"多平台发布"底座的三张表（批次 18）：

  - ``publish_channels``  渠道配置（凭据加密存储，永不回传）
  - ``publish_tasks``     发布任务（同一文章 + 渠道唯一，重试复用同一条）
  - ``publish_logs``      每次尝试的结果记录

外键一律 ``ON DELETE CASCADE``：删文章 / 删渠道 / 删任务时不留孤儿行
（批次 17 的教训 —— ``chat_messages.group`` 缺级联曾让群删除 500）。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d9e5f7a2b4"
down_revision = "b8e6f2a4c9d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publish_channels",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="渠道 ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="渠道名"),
        sa.Column("platform", sa.String(length=32), nullable=False, comment="平台标识"),
        sa.Column("endpoint", sa.String(length=255), nullable=True, comment="API 基址覆盖"),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True, comment="凭据（加密）"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=True, comment="是否启用"),
        sa.Column("created_by", sa.BigInteger(), nullable=True, comment="创建人 ID"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_publish_channels_platform_name",
        "publish_channels",
        ["platform", "name"],
        unique=True,
    )

    op.create_table(
        "publish_tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="任务 ID"),
        sa.Column("article_id", sa.BigInteger(), nullable=False, comment="文章 ID"),
        sa.Column("channel_id", sa.BigInteger(), nullable=False, comment="渠道 ID"),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=True,
            comment="状态",
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=True, comment="尝试次数"),
        sa.Column("last_error", sa.String(length=500), nullable=True, comment="最近失败原因"),
        sa.Column("external_id", sa.String(length=128), nullable=True, comment="平台侧文档 ID"),
        sa.Column("external_url", sa.String(length=500), nullable=True, comment="平台侧链接"),
        sa.Column("payload", sa.Text(), nullable=True, comment="发布载荷快照（JSON）"),
        sa.Column("created_by", sa.BigInteger(), nullable=True, comment="创建人 ID"),
        sa.Column("started_at", sa.DateTime(), nullable=True, comment="最近开始时间"),
        sa.Column("finished_at", sa.DateTime(), nullable=True, comment="最近结束时间"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["publish_channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_publish_tasks_article_channel",
        "publish_tasks",
        ["article_id", "channel_id"],
        unique=True,
    )
    op.create_index(
        "idx_publish_tasks_status_created", "publish_tasks", ["status", "created_at"]
    )

    op.create_table(
        "publish_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="日志 ID"),
        sa.Column("task_id", sa.BigInteger(), nullable=False, comment="发布任务 ID"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="本次结果"),
        sa.Column("message", sa.Text(), nullable=True, comment="结果说明 / 错误信息"),
        sa.Column("duration_ms", sa.Integer(), nullable=True, comment="耗时（毫秒）"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.ForeignKeyConstraint(["task_id"], ["publish_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_publish_logs_task_created", "publish_logs", ["task_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_publish_logs_task_created", table_name="publish_logs")
    op.drop_table("publish_logs")
    op.drop_index("idx_publish_tasks_status_created", table_name="publish_tasks")
    op.drop_index("idx_publish_tasks_article_channel", table_name="publish_tasks")
    op.drop_table("publish_tasks")
    op.drop_index("idx_publish_channels_platform_name", table_name="publish_channels")
    op.drop_table("publish_channels")
