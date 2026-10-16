"""add audit log hash chain and before/after snapshots

Revision ID: d4e9a1c7f2b8
Revises: c8d2e5f7b913
Create Date: 2026-10-14 00:00:00.000000

给 ``audit_logs`` 补上企业审计要求的三项能力：

1. ``before_data`` / ``after_data`` —— 变更前后值快照（JSON 文本）。原先路由级审计
   只记 ``"{method} {path}"``，无法回答"谁在何时把什么从 A 改成了 B"。
2. ``prev_hash`` / ``entry_hash`` —— 哈希链。每条记录的 ``entry_hash`` 覆盖
   ``prev_hash`` 与自身内容，任何历史行被改动都会让后续链断裂，
   由 ``AuditLogService.verify_chain`` 检出。

四列全部 ``nullable``：历史记录没有这些值，加列不应让升级失败；链校验从启用后的
第一条记录开始（`entry_hash` 为空的历史行按边界处理）。

模型侧手工追加这些列（并已在 ``config/models.yaml`` 登记）—— 为加列而重新生成整个
模型会覆盖文件。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e9a1c7f2b8'
down_revision: Union[str, Sequence[str], None] = 'c8d2e5f7b913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'audit_logs',
        sa.Column('before_data', sa.Text(), nullable=True, doc='变更前值快照 (JSON)'),
    )
    op.add_column(
        'audit_logs',
        sa.Column('after_data', sa.Text(), nullable=True, doc='变更后值快照 (JSON)'),
    )
    op.add_column(
        'audit_logs',
        sa.Column(
            'prev_hash',
            sa.String(length=64),
            nullable=True,
            doc='前一条审计记录的 entry_hash（哈希链；空表示链首）',
        ),
    )
    op.add_column(
        'audit_logs',
        sa.Column(
            'entry_hash',
            sa.String(length=64),
            nullable=True,
            doc='本条记录的 sha256 摘要（含 prev_hash，用于篡改检测）',
        ),
    )
    op.create_index('idx_audit_logs_entry_hash', 'audit_logs', ['entry_hash'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_audit_logs_entry_hash', table_name='audit_logs')
    op.drop_column('audit_logs', 'entry_hash')
    op.drop_column('audit_logs', 'prev_hash')
    op.drop_column('audit_logs', 'after_data')
    op.drop_column('audit_logs', 'before_data')
