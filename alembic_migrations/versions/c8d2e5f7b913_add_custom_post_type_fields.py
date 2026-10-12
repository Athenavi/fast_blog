"""add custom post type fields

Revision ID: c8d2e5f7b913
Revises: b7f3c9e1a204
Create Date: 2026-10-12 21:50:00.000000

给 ``custom_post_types`` 增加 ``fields``：字段定义（JSON 数组文本），
让站长能**不写代码**定义自定义内容类型的字段（P1-3 内容建模器）。

字段定义形如::

    [{"key": "price", "type": "number", "label": "价格", "required": true, "min": 0},
     {"key": "tags", "type": "relation", "label": "标签", "target": "tag", "multiple": true}]

取值仍落在既有的 ``custom_fields``（EAV），写入前由
``src/api/v3/modules/content/custom_post_type/field_spec.py`` 按定义校验。

模型侧手工追加该列（并已在 config/models.yaml 登记）：为加一列而重新生成整个模型会
覆盖文件、且无 relationship 的模型会漏 ``Base`` 导入。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8d2e5f7b913'
down_revision: Union[str, Sequence[str], None] = 'b7f3c9e1a204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'custom_post_types',
        sa.Column('fields', sa.String(length=4000), nullable=True, doc='字段定义（JSON 数组文本）'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('custom_post_types', 'fields')
