"""add permission groups and roles data_scope

Revision ID: 5b684d5fa98b
Revises: dba7d5c907ac
Create Date: 2026-09-18 15:23:06.393397

本迁移**只含权限重构 P2 的变更**：权限用户组三张表 + ``roles.data_scope``。

说明：``alembic revision --autogenerate`` 的输出里还夹带了若干**与本次无关的历史漂移**
（``users.totp_secret`` 的 TEXT→VARCHAR(32) 类型变更、``vip_subscriptions`` 的 4 个索引、
``roles.idx_roles_slug`` / ``users.idx_users_username`` 的 "索引↔唯一约束" 表述差异），
这些已**手工剔除**：把无关的结构变更混进权限迁移，会让回滚边界与故障定位都变得不可控，
其中 ``totp_secret`` 的类型收窄还可能损坏既有数据。

权限模型（``config/models.yaml``）与本次 DDL 一一对应：

  - ``permission_groups``：权限用户组（树形，替代官方的"部门"），承载数据范围
  - ``user_group_members``：用户 ↔ 组（一人多组）
  - ``role_groups``：角色 ↔ 组（``data_scope=5`` 自定义范围时使用）
  - ``roles.data_scope``：1 仅本人 / 2 本组及以下 / 3 全部 / 5 自定义组
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b684d5fa98b"
down_revision: Union[str, Sequence[str], None] = "dba7d5c907ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增权限用户组三表，并为 roles 增加 data_scope"""
    # ------------------------------------------------------------------ 权限用户组
    op.create_table(
        "permission_groups",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("code", sa.String(length=100), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("sort_order", sa.BigInteger(), nullable=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["permission_groups.id"]),
        sa.PrimaryKeyConstraint("id"),
        # 唯一性只用一个**命名**约束：同名 index + constraint 在 PostgreSQL 下会冲突
        sa.UniqueConstraint("code", name="idx_permission_groups_code"),
    )
    op.create_index("idx_permission_groups_active", "permission_groups", ["is_active"])
    op.create_index("idx_permission_groups_parent", "permission_groups", ["parent_id"])
    op.create_index("idx_permission_groups_sort", "permission_groups", ["sort_order"])

    # ------------------------------------------------------------------ 用户 ↔ 组
    op.create_table(
        "user_group_members",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("group_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["permission_groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "group_id", name="idx_user_group_members_unique"),
    )
    op.create_index("idx_user_group_members_user", "user_group_members", ["user_id"])
    op.create_index("idx_user_group_members_group", "user_group_members", ["group_id"])

    # ------------------------------------------------------------------ 角色 ↔ 组
    op.create_table(
        "role_groups",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=True),
        sa.Column("group_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["permission_groups.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "group_id", name="idx_role_groups_unique"),
    )
    op.create_index("idx_role_groups_role", "role_groups", ["role_id"])
    op.create_index("idx_role_groups_group", "role_groups", ["group_id"])

    # ------------------------------------------------------------------ roles.data_scope
    # nullable=True 与 config/models.yaml 生成的模型保持一致（生成器当前无法为 integer 字段
    # 表达 NOT NULL，见方案里的“生成器已知缺陷”）；server_default='1'（仅本人）保证既有角色行
    # 被安全填充，业务层再把 NULL 兜底为“仅本人”。
    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("data_scope", sa.Integer(), nullable=True, server_default="1")
        )


def downgrade() -> None:
    """回滚：删除 roles.data_scope 与权限用户组三表"""
    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.drop_column("data_scope")

    op.drop_index("idx_role_groups_group", table_name="role_groups")
    op.drop_index("idx_role_groups_role", table_name="role_groups")
    op.drop_table("role_groups")

    op.drop_index("idx_user_group_members_group", table_name="user_group_members")
    op.drop_index("idx_user_group_members_user", table_name="user_group_members")
    op.drop_table("user_group_members")

    op.drop_index("idx_permission_groups_sort", table_name="permission_groups")
    op.drop_index("idx_permission_groups_parent", table_name="permission_groups")
    op.drop_index("idx_permission_groups_active", table_name="permission_groups")
    op.drop_table("permission_groups")
