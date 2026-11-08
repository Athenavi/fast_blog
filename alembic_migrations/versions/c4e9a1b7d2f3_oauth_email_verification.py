"""oauth accounts: add is_email_verified

OAuth 自助建号允许直接登录，但必须在 24 小时内完成邮箱验证（`is_email_verified=False`）。
存量账号与后台/CLI 建号一律视为已验证，因此列默认值取 true。

Revision ID: c4e9a1b7d2f3
Revises: a7c2f1d4e9b0
Create Date: 2026-11-09
"""

import sqlalchemy as sa
from alembic import op

revision = "c4e9a1b7d2f3"
down_revision = "a7c2f1d4e9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="邮箱是否已验证",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_email_verified")
