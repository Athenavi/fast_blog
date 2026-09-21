"""ai_configs: connection fields for custom LLM endpoints

Revision ID: a7c1f2b4d5e6
Revises: e5b7c9d1f3a6
Create Date: 2026-09-21

给 ``ai_configs`` 加三个「自定义连接」字段（批次 20：AI 真实调用）：

  - ``api_version``：Anthropic 走 ``anthropic-version`` 头，OpenAI 兼容端点（Azure）走
    ``api-version`` query；
  - ``extra_headers``：自定义请求头（JSON），用于 Azure 的 ``api-key``、自建网关的鉴权头等；
  - ``max_tokens``：单次调用最大输出 token（``server_default=1024``，既有行自动补值）。

模型定义同步在 ``config/models.yaml`` 与 ``shared/models/ai/ai_config.py``。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c1f2b4d5e6"
down_revision = "e5b7c9d1f3a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_configs",
        sa.Column("api_version", sa.String(length=100), nullable=True, comment="API 版本"),
    )
    op.add_column(
        "ai_configs",
        sa.Column("extra_headers", sa.Text(), nullable=True, comment="自定义请求头（JSON）"),
    )
    op.add_column(
        "ai_configs",
        sa.Column(
            "max_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1024"),
            comment="单次调用最大输出 token",
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_configs", "max_tokens")
    op.drop_column("ai_configs", "extra_headers")
    op.drop_column("ai_configs", "api_version")
