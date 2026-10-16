"""add seo redirects

Revision ID: 375ce7e93b09
Revises: 50dc796822dc
Create Date: 2026-09-29 06:51:41.212809

为「多格式迁移」新增 ``seo_redirects``：导入时按源站 URL 生成旧链接 → 新链接的跳转，
取代 v2 的 ``redirects.json`` 文件存储（非 DB）。``from_path`` 唯一，重复导入走更新。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '375ce7e93b09'
down_revision: Union[str, Sequence[str], None] = '50dc796822dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'seo_redirects',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, doc='规则 ID'),
        sa.Column('from_path', sa.String(length=500), nullable=False, doc='源路径'),
        sa.Column('to_path', sa.String(length=500), nullable=False, doc='目标路径或绝对 URL'),
        sa.Column('status_code', sa.Integer(), nullable=False, doc='HTTP 状态码'),
        sa.Column('is_active', sa.Boolean(), nullable=False, doc='是否启用'),
        sa.Column('hits', sa.BigInteger(), nullable=False, doc='命中次数'),
        sa.Column('source', sa.String(length=50), nullable=False, doc='来源（manual/migration）'),
        sa.Column('source_reference', sa.String(length=500), nullable=True, doc='来源说明'),
        sa.Column('notes', sa.Text(), nullable=True, doc='备注'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, doc='创建者用户 ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, doc='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, doc='更新时间'),
        sa.ForeignKeyConstraint(
            ['created_by'], ['users.id'],
            name='seo_redirects_created_by_fkey', ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_seo_redirects_from_path', 'seo_redirects', ['from_path'], unique=True)
    op.create_index('idx_seo_redirects_active', 'seo_redirects', ['is_active'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_seo_redirects_active', table_name='seo_redirects')
    op.drop_index('idx_seo_redirects_from_path', table_name='seo_redirects')
    op.drop_table('seo_redirects')
