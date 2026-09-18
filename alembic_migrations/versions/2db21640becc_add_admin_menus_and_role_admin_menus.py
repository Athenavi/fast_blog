"""add admin_menus and role_admin_menus

Revision ID: 2db21640becc
Revises: 5b684d5fa98b
Create Date: 2026-09-18

P3（权限重构）：新增后台菜单授权载体 `admin_menus` 与角色-菜单关联 `role_admin_menus`。

本迁移**只包含本次新增的两张表**。autogenerate 产生的其余差异均与本次变更无关，
已手工剔除（与上一版迁移同一口径）：

  - `permission_groups` / `user_group_members` 的 `unique constraint ↔ unique index` 表述差异
    —— 生成器缺陷④：模型侧同时声明了同名 ``UniqueConstraint`` 与 ``Index``，属长期漂移，留待 P6 修生成器
  - `vip_subscriptions` 的 4 个历史索引漂移

为与上一版迁移保持一致：命名唯一约束用 ``UniqueConstraint``（不重复创建同名 ``Index``）。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2db21640becc"
down_revision: Union[str, Sequence[str], None] = "5b684d5fa98b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "admin_menus",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=100), nullable=True),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("menu_type", sa.Integer(), nullable=True),
        sa.Column("permission_code", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["admin_menus.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="idx_admin_menus_code"),
    )
    op.create_index("idx_admin_menus_parent", "admin_menus", ["parent_id"], unique=False)
    op.create_index("idx_admin_menus_active", "admin_menus", ["is_active"], unique=False)
    op.create_index("idx_admin_menus_sort", "admin_menus", ["sort_order"], unique=False)

    op.create_table(
        "role_admin_menus",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=True),
        sa.Column("admin_menu_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["admin_menu_id"], ["admin_menus.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "admin_menu_id", name="idx_role_admin_menus_unique"),
    )
    op.create_index("idx_role_admin_menus_role", "role_admin_menus", ["role_id"], unique=False)
    op.create_index("idx_role_admin_menus_menu", "role_admin_menus", ["admin_menu_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_role_admin_menus_menu", table_name="role_admin_menus")
    op.drop_index("idx_role_admin_menus_role", table_name="role_admin_menus")
    op.drop_table("role_admin_menus")

    op.drop_index("idx_admin_menus_sort", table_name="admin_menus")
    op.drop_index("idx_admin_menus_active", table_name="admin_menus")
    op.drop_index("idx_admin_menus_parent", table_name="admin_menus")
    op.drop_table("admin_menus")
