"""add analytics table indexes

Revision ID: a1c4f7b2e903
Revises: 375ce7e93b09
Create Date: 2026-10-12 16:40:00.000000

为两张高频分析表补索引：``page_views``（每次访问写一行）与 ``user_activities``。
此前两者除主键外没有任何索引，而分析/统计查询基本都按 ``created_at``、``user``
过滤与聚合，数据量上来后会退化为全表扫描。

模型侧对应手工补充的 ``__table_args__``（见
``shared/models/analytics/page_view.py`` 与 ``user_activity.py``）。
注意这两个模型由代码生成器产出，重新生成时需要同步 ``config/models.yaml``。
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1c4f7b2e903'
down_revision: Union[str, Sequence[str], None] = '375ce7e93b09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: (表名, 索引名, 列名列表)
_INDEXES = [
    ("page_views", "idx_page_views_created_at", ["created_at"]),
    ("page_views", "idx_page_views_user_created", ["user", "created_at"]),
    ("page_views", "idx_page_views_session", ["session_id"]),
    ("user_activities", "idx_user_activities_created_at", ["created_at"]),
    ("user_activities", "idx_user_activities_user_created", ["user", "created_at"]),
    ("user_activities", "idx_user_activities_type_created", ["activity_type", "created_at"]),
]


def upgrade() -> None:
    """Upgrade schema."""
    for table, name, columns in _INDEXES:
        op.create_index(name, table, columns)


def downgrade() -> None:
    """Downgrade schema."""
    for table, name, _ in _INDEXES:
        op.drop_index(name, table_name=table)
