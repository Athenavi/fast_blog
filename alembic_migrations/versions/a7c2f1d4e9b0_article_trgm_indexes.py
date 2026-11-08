"""article keyword search: pg_trgm indexes

`public_list` 的关键词搜索是 `title ILIKE '%kw%'` + `excerpt ILIKE '%kw%'`，
前缀通配的 LIKE 用不上 B-Tree，全表扫描随文章数线性变慢。`pg_trgm` 的 GIN 索引
正是为 `%kw%` 这类匹配设计的。

Revision ID: a7c2f1d4e9b0
Revises: e5f1b8c93a07
Create Date: 2026-11-09
"""

from alembic import op

revision = "a7c2f1d4e9b0"
down_revision = "e5f1b8c93a07"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        # 非 PostgreSQL 部署（测试/本地 sqlite）没有 pg_trgm，跳过即可
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # 不用 CONCURRENTLY：alembic 在事务里执行，CONCURRENTLY 不允许。
    # 建索引会短暂阻塞 articles 的写入，升级窗口内可接受。
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_title_trgm "
        "ON articles USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_excerpt_trgm "
        "ON articles USING gin (excerpt gin_trgm_ops)"
    )


def downgrade() -> None:
    if not _is_postgres():
        return
    op.execute("DROP INDEX IF EXISTS idx_articles_excerpt_trgm")
    op.execute("DROP INDEX IF EXISTS idx_articles_title_trgm")
