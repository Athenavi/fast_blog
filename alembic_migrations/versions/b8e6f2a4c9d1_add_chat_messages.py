"""add chat messages

Revision ID: b8e6f2a4c9d1
Revises: f7b2c4d8e1a5
Create Date: 2026-09-20

新增批次 17 的**群聊消息**表：

  - ``chat_messages``  群消息（软删除撤回；实时广播走 Redis，不落表）

`chat_groups` / `chat_group_members` 早在批次 4 就存在，本表只补"消息"这一段。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8e6f2a4c9d1"
down_revision = "f7b2c4d8e1a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="消息 ID"),
        sa.Column("group", sa.BigInteger(), nullable=False, comment="群聊 ID"),
        sa.Column("user", sa.BigInteger(), nullable=False, comment="发送者 ID"),
        sa.Column("content", sa.Text(), nullable=False, comment="消息内容"),
        sa.Column(
            "message_type", sa.String(length=50), server_default="text", nullable=True, comment="消息类型"
        ),
        sa.Column("attachment_url", sa.String(length=500), nullable=True, comment="附件 URL"),
        sa.Column("parent_message", sa.BigInteger(), nullable=True, comment="引用的消息 ID"),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.false(), nullable=True, comment="是否已撤回"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        # 群被解散时消息一并删除（否则新表的外键会挡住 `DELETE /chat/group/{id}`）；
        # 被引用的消息删除时回复链置空（不连带删回复）。
        sa.ForeignKeyConstraint(["group"], ["chat_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user"], ["users.id"]),
        sa.ForeignKeyConstraint(["parent_message"], ["chat_messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_chat_messages_group_created", "chat_messages", ["group", "created_at"]
    )
    op.create_index("idx_chat_messages_user_created", "chat_messages", ["user", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_chat_messages_user_created", table_name="chat_messages")
    op.drop_index("idx_chat_messages_group_created", table_name="chat_messages")
    op.drop_table("chat_messages")
