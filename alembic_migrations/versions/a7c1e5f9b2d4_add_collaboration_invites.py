"""add collaboration_invites

Revision ID: a7c1e5f9b2d4
Revises: e4f2b8a1c9d3
Create Date: 2026-09-20

只新增 ``collaboration_invites`` 一张表（协作邀请：文章协作编辑 / 工作区邀请）。

``invite_code`` 走 **命名 UniqueConstraint**（与模型声明一致），因此这里不再
重复 ``create_index(unique=True)``，避免同名对象冲突。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c1e5f9b2d4"
down_revision = "e4f2b8a1c9d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collaboration_invites",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="邀请 ID"),
        sa.Column("invite_code", sa.String(length=64), nullable=False, comment="邀请码（唯一）"),
        sa.Column(
            "target_type",
            sa.String(length=50),
            nullable=False,
            comment="目标类型 (article/workspace)",
        ),
        sa.Column("target_id", sa.BigInteger(), nullable=False, comment="目标 ID"),
        sa.Column(
            "permission",
            sa.String(length=20),
            server_default="edit",
            nullable=True,
            comment="权限 (view/edit)",
        ),
        sa.Column("creator_id", sa.BigInteger(), nullable=True, comment="创建人"),
        sa.Column("expires_at", sa.DateTime(), nullable=True, comment="过期时间"),
        sa.Column(
            "max_uses",
            sa.Integer(),
            server_default="0",
            nullable=True,
            comment="最大使用次数 (0 = 不限)",
        ),
        sa.Column(
            "use_count", sa.Integer(), server_default="0", nullable=True, comment="已使用次数"
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=True,
            comment="是否激活",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code", name="idx_collaboration_invites_code"),
    )
    op.create_index(
        "idx_collaboration_invites_target",
        "collaboration_invites",
        ["target_type", "target_id"],
    )
    op.create_index("idx_collaboration_invites_active", "collaboration_invites", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_collaboration_invites_active", table_name="collaboration_invites")
    op.drop_index("idx_collaboration_invites_target", table_name="collaboration_invites")
    op.drop_table("collaboration_invites")
