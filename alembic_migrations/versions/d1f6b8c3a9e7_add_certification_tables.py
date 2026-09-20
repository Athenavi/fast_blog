"""add certification tables (expert certification)

Revision ID: d1f6b8c3a9e7
Revises: c8e4a2b6d1f3
Create Date: 2026-09-20

新增 T5-11 批次 13 的**专家认证**三张表：

  - ``expert_certifications``   认证主表（状态机 pending → approved / rejected → revoked）
  - ``certification_documents`` 证明材料（只存媒体库文件引用）
  - ``certification_reviews``   审核流水（可追溯谁在何时改成了什么）

v2 完全没有任何对应表（内存单例），所以这是**从零建**。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d1f6b8c3a9e7"
down_revision = "c8e4a2b6d1f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------- 认证主表
    op.create_table(
        "expert_certifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="认证 ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="申请人 ID"),
        sa.Column("cert_type", sa.String(length=50), nullable=False, comment="认证类型"),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=True, comment="状态"),
        sa.Column("real_name", sa.String(length=100), nullable=True, comment="真实姓名"),
        sa.Column("id_number", sa.String(length=64), nullable=True, comment="证件号码（敏感）"),
        sa.Column("phone", sa.String(length=32), nullable=True, comment="联系电话"),
        sa.Column("email", sa.String(length=255), nullable=True, comment="联系邮箱"),
        sa.Column("organization", sa.String(length=255), nullable=True, comment="所在机构"),
        sa.Column("position", sa.String(length=100), nullable=True, comment="职务"),
        sa.Column("department", sa.String(length=100), nullable=True, comment="部门"),
        sa.Column("work_years", sa.Integer(), server_default="0", nullable=True, comment="从业年限"),
        sa.Column("intro", sa.Text(), nullable=True, comment="个人简介"),
        sa.Column("achievements", sa.Text(), nullable=True, comment="代表成果"),
        sa.Column("portfolio_url", sa.String(length=500), nullable=True, comment="作品集链接"),
        sa.Column("applied_at", sa.DateTime(), nullable=True, comment="申请时间"),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="最近审核时间"),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=True, comment="最近审核人 ID"),
        sa.Column("review_comment", sa.String(length=500), nullable=True, comment="审核意见"),
        sa.Column("issued_at", sa.DateTime(), nullable=True, comment="通过时间"),
        sa.Column("expires_at", sa.DateTime(), nullable=True, comment="有效期至"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_expert_certifications_user_status", "expert_certifications", ["user_id", "status"]
    )
    op.create_index("idx_expert_certifications_status", "expert_certifications", ["status"])
    op.create_index("idx_expert_certifications_type", "expert_certifications", ["cert_type"])

    # ---------------------------------------------------------------- 证明材料
    op.create_table(
        "certification_documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="材料 ID"),
        sa.Column("certification_id", sa.BigInteger(), nullable=False, comment="认证 ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="上传者 ID"),
        sa.Column("file_name", sa.String(length=255), nullable=True, comment="文件名"),
        sa.Column("file_url", sa.String(length=500), nullable=False, comment="文件地址"),
        sa.Column("file_type", sa.String(length=50), nullable=True, comment="MIME 类型"),
        sa.Column("file_size", sa.BigInteger(), server_default="0", nullable=True, comment="文件大小"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["certification_id"], ["expert_certifications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_certification_documents_cert", "certification_documents", ["certification_id"])

    # ---------------------------------------------------------------- 审核流水
    op.create_table(
        "certification_reviews",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="记录 ID"),
        sa.Column("certification_id", sa.BigInteger(), nullable=False, comment="认证 ID"),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=True, comment="审核人 ID"),
        sa.Column("action", sa.String(length=20), nullable=True, comment="动作"),
        sa.Column("comment", sa.String(length=500), nullable=True, comment="意见"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["certification_id"], ["expert_certifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_certification_reviews_cert", "certification_reviews", ["certification_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_certification_reviews_cert", table_name="certification_reviews")
    op.drop_table("certification_reviews")

    op.drop_index("idx_certification_documents_cert", table_name="certification_documents")
    op.drop_table("certification_documents")

    op.drop_index("idx_expert_certifications_type", table_name="expert_certifications")
    op.drop_index("idx_expert_certifications_status", table_name="expert_certifications")
    op.drop_index("idx_expert_certifications_user_status", table_name="expert_certifications")
    op.drop_table("expert_certifications")
