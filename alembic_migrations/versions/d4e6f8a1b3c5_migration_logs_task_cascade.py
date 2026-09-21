"""migration_logs task_id cascade

Revision ID: d4e6f8a1b3c5
Revises: c3d9e5f7a2b4
Create Date: 2026-09-21

把 ``migration_logs.task_id`` 的外键改成 ``ON DELETE CASCADE``（批次 18 实测缺陷）：

删除一个有日志的迁移任务时，旧外键让 PostgreSQL 抛
``ForeignKeyViolationError`` → 接口 500（与批次 17 的 ``chat_messages.group`` 是同一类问题）。

> ``migration_logs`` 是早期批次建的表，外键当时没写 ``ondelete``。历史日志行与新外键
> 不冲突（约束是即时校验的：既有的引用都跟着任务存在）。
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e6f8a1b3c5"
down_revision = "c3d9e5f7a2b4"
branch_labels = None
depends_on = None

FK_NAME = "migration_logs_task_id_fkey"


def upgrade() -> None:
    op.drop_constraint(FK_NAME, "migration_logs", type_="foreignkey")
    op.create_foreign_key(
        FK_NAME,
        "migration_logs",
        "migration_tasks",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(FK_NAME, "migration_logs", type_="foreignkey")
    op.create_foreign_key(
        FK_NAME,
        "migration_logs",
        "migration_tasks",
        ["task_id"],
        ["id"],
    )
