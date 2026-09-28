"""add article preview tokens

Revision ID: 50dc796822dc
Revises: 8b7ecb6d053c
Create Date: 2026-09-28 21:12:59.418748

为「草稿预览令牌」新增 ``article_preview_tokens``（替代 v2 的 ``data/preview_tokens.json``
文件存储）。归属与级联显式声明：文章删除级联删令牌，创建者删除置 NULL。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '50dc796822dc'
down_revision: Union[str, Sequence[str], None] = '8b7ecb6d053c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'article_preview_tokens',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, doc='令牌 ID'),
        sa.Column('article_id', sa.BigInteger(), nullable=False, doc='文章 ID'),
        sa.Column('token', sa.String(length=64), nullable=False, doc='预览令牌（URL 安全随机串）'),
        sa.Column('password_hash', sa.String(length=255), nullable=True, doc='访问密码的 Argon2 哈希'),
        sa.Column('max_views', sa.BigInteger(), nullable=True, doc='最大访问次数（为空表示不限）'),
        sa.Column('view_count', sa.BigInteger(), nullable=False, doc='已访问次数'),
        sa.Column('is_active', sa.Boolean(), nullable=False, doc='是否有效'),
        sa.Column('expires_at', sa.DateTime(), nullable=False, doc='过期时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, doc='创建者用户 ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, doc='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, doc='更新时间'),
        sa.ForeignKeyConstraint(
            ['article_id'], ['articles.id'],
            name='article_preview_tokens_article_id_fkey', ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'], ['users.id'],
            name='article_preview_tokens_created_by_fkey', ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token', name='article_preview_tokens_token_key'),
    )
    op.create_index(
        'idx_article_preview_tokens_article', 'article_preview_tokens', ['article_id'], unique=False
    )
    op.create_index(
        'idx_article_preview_tokens_expires', 'article_preview_tokens', ['expires_at'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_article_preview_tokens_expires', table_name='article_preview_tokens')
    op.drop_index('idx_article_preview_tokens_article', table_name='article_preview_tokens')
    op.drop_table('article_preview_tokens')
