"""add shortcodes

Revision ID: e4f2b8a1c9d3
Revises: 2db21640becc
Create Date: 2026-09-20

v3 content/shortcode 模块：短代码库（``[code]`` -> 预定义内容片段，参考 WordPress shortcode）。

本迁移只新增 `shortcodes` 一张表。与上一版迁移（2db21640becc）同一口径：
命名唯一约束用 ``UniqueConstraint``（不重复创建同名 ``Index``）。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4f2b8a1c9d3"
down_revision: Union[str, Sequence[str], None] = "2db21640becc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "shortcodes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="idx_shortcodes_code"),
    )
    op.create_index("idx_shortcodes_is_active", "shortcodes", ["is_active"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_shortcodes_is_active", table_name="shortcodes")
    op.drop_table("shortcodes")
