"""system_settings.setting_value to text

Revision ID: e5b7c9d1f3a6
Revises: d4e6f8a1b3c5
Create Date: 2026-09-21

把 ``system_settings.setting_value`` 从 ``VARCHAR(255)`` 扩成 ``TEXT``（批次 18 实测缺陷）：

``setting_value`` 同时承载 **JSON 配置**（例如 ``cdn.config``：provider + zone_id + 加密后的
api_token + settings），一旦序列化超过 255 字符，保存就抛
``StringDataRightTruncationError`` → 接口 500。

> 全表只有这一列需要放宽；PG 的 ``ALTER COLUMN TYPE text`` 是元数据级操作，不改写数据。
> downgrade 会退回 ``VARCHAR(255)``，**若库里已有超长值会失败**（这是刻意的：宁可报错也不静默截断）。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5b7c9d1f3a6"
down_revision = "d4e6f8a1b3c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "system_settings",
        "setting_value",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "system_settings",
        "setting_value",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
