"""add api tokens

Revision ID: b7f3c9e1a204
Revises: a1c4f7b2e903
Create Date: 2026-10-12 21:10:00.000000

新增 ``api_tokens``：对外 API 令牌（第三方应用 / CI 接入）。

与前缀展示、撤销、审计相关的设计取舍：

  - **只存哈希**（``token_hash``，Argon2）：明文仅在创建响应里返回一次；
    ``token_prefix`` 只取明文前若干字符，用于列表展示与人工识别。
  - ``scopes`` 存**权限码子集**（JSON 数组文本）：授予范围不得超过归属用户的权限；
    校验在 ``src/api/v3/core/permission/control.py`` 内 fail-closed。
  - ``expires_at`` 允许为空（不过期），但管理端点默认强制 90 天，避免长期凭证。

模型侧对应 ``shared/models/security/api_token.py``（由生成器产出后手工补齐 Base 导入），
登记于 ``config/models.yaml``。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7f3c9e1a204'
down_revision: Union[str, Sequence[str], None] = 'a1c4f7b2e903'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'api_tokens',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, doc='令牌 ID'),
        sa.Column('name', sa.String(length=100), nullable=True, doc='用途备注'),
        sa.Column('token_prefix', sa.String(length=16), nullable=True, doc='明文前缀（仅用于展示与检索）'),
        sa.Column('token_hash', sa.String(length=255), nullable=True, doc='令牌哈希（argon2；不存明文）'),
        sa.Column('scopes', sa.String(length=2000), nullable=True, doc='权限码子集（JSON 数组文本）'),
        sa.Column('user_id', sa.BigInteger(), nullable=True, doc='归属用户'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, doc='过期时间（留空 = 不过期）'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, doc='最近使用时间'),
        sa.Column('is_active', sa.Boolean(), nullable=True, doc='是否启用'),
        sa.Column('created_at', sa.DateTime(), nullable=True, doc='创建时间'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index('idx_api_tokens_prefix', 'api_tokens', ['token_prefix'])
    op.create_index('idx_api_tokens_user', 'api_tokens', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_api_tokens_user', table_name='api_tokens')
    op.drop_index('idx_api_tokens_prefix', table_name='api_tokens')
    op.drop_table('api_tokens')
