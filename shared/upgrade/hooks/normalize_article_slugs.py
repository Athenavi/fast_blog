"""
规范化文章 slug — 确保所有 slug 为小写
"""
from shared.upgrade import data_migration


@data_migration(name="normalize-article-slugs", priority=100)
def normalize_article_slugs(db):
    """确保所有 slug 为小写且去重（添加后缀）"""
    from shared.models.article import Article
    from sqlalchemy import select, text

    # 检查是否有大写 slug
    result = db.execute(
        text("SELECT COUNT(*) FROM articles WHERE slug != LOWER(slug)")
    )
    if result.scalar() == 0:
        return 0  # 幂等 — 无事可做

    # 获取所有需要修复的记录
    rows = db.execute(
        text("SELECT id, slug FROM articles WHERE slug != LOWER(slug)")
    ).all()

    count = 0
    for row in rows:
        new_slug = row.slug.lower()
        exists = db.execute(
            text("SELECT COUNT(*) FROM articles WHERE slug = :slug AND id != :id"),
            {"slug": new_slug, "id": row.id},
        ).scalar()
        if exists:
            new_slug = f"{new_slug}-{row.id}"
        db.execute(
            text("UPDATE articles SET slug = :slug WHERE id = :id"),
            {"slug": new_slug, "id": row.id},
        )
        count += 1

    return count
