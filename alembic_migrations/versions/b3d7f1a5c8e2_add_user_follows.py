"""add user_follows

Revision ID: b3d7f1a5c8e2
Revises: a7c1e5f9b2d4
Create Date: 2026-09-20

只新增 ``user_follows`` 一张表（前台关注关系，fans）。

``(follower, following)`` 走**命名 UniqueConstraint**，因此这里不再重复
``create_index(unique=True)``，避免同名对象冲突。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3d7f1a5c8e2"
down_revision = "a7c1e5f9b2d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_follows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="关注 ID"),
        sa.Column("follower", sa.BigInteger(), nullable=True, comment="关注者（发起方）"),
        sa.Column("following", sa.BigInteger(), nullable=True, comment="被关注者（目标）"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="关注时间"),
        sa.ForeignKeyConstraint(["follower"], ["users.id"]),
        sa.ForeignKeyConstraint(["following"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("follower", "following", name="idx_user_follows_unique"),
    )
    op.create_index("idx_user_follows_following", "user_follows", ["following"])
    op.create_index("idx_user_follows_created", "user_follows", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_user_follows_created", table_name="user_follows")
    op.drop_index("idx_user_follows_following", table_name="user_follows")
    op.drop_table("user_follows")
