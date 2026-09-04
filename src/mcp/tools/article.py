"""
MCP 文章工具处理器
权限：所有操作需要用户上下文，删除/更新需要本人或管理员
"""
from datetime import datetime

from sqlalchemy import select

from shared.models.article import Article, ArticleContent
from src.mcp._context import get_user_ctx
from src.utils.database.unified_manager import db_manager


def _require_auth():
    """确保用户已认证"""
    ctx = get_user_ctx()
    if not ctx:
        raise PermissionError("需要登录才能执行此操作")
    return ctx


async def create_article(arguments: dict) -> dict:
    """创建新文章（需登录）"""
    ctx = _require_auth()
    title = (arguments.get("title") or "").strip()
    content = (arguments.get("content") or "").strip()
    if not title:
        raise ValueError("文章标题不能为空")
    if not content:
        raise ValueError("文章内容不能为空")

    now = datetime.utcnow()
    slug = title.lower().replace(" ", "-")[:200]
    status_str = arguments.get("status", "draft")

    async with db_manager.get_session() as db:
        try:
            article = Article(
                title=title, slug=slug, excerpt=content[:200], user=ctx.id,
                category=arguments.get("category_id"), tags_list=arguments.get("tags", "").split(",") if arguments.get("tags") else [],
                status=1 if status_str == "published" else 0, created_at=now, updated_at=now,
            )
            db.add(article)
            await db.flush()

            db.add(ArticleContent(article=article.id, content=content, created_at=now, updated_at=now))
            await db.commit()

            return {"success": True, "message": f"文章「{title}」创建成功",
                    "article_id": article.id, "status": status_str}
        except Exception as e:
            await db.rollback()
            raise ValueError(f"创建文章失败: {e}")


async def update_article(arguments: dict) -> dict:
    """更新文章（仅作者或管理员）"""
    ctx = _require_auth()
    article_id = arguments.get("article_id")
    if not article_id:
        raise ValueError("文章ID不能为空")

    now = datetime.utcnow()
    async with db_manager.get_session() as db:
        article = await db.scalar(select(Article).where(Article.id == int(article_id)))
        if not article:
            raise ValueError(f"文章 #{article_id} 不存在")
        if article.user != ctx.id and not ctx.is_superuser:
            raise PermissionError("只能编辑自己的文章")

        if "title" in arguments:
            article.title = arguments["title"].strip()
        if "status" in arguments:
            article.status = 1 if arguments["status"] == "published" else 0
        if "content" in arguments:
            text = arguments["content"].strip()
            ac = await db.scalar(select(ArticleContent).where(ArticleContent.article == int(article_id)))
            if ac:
                ac.content = text
                ac.updated_at = now
            else:
                db.add(ArticleContent(article=int(article_id), content=text, created_at=now, updated_at=now))

        article.updated_at = now
        await db.commit()
        return {"success": True, "message": f"文章 #{article_id} 更新成功", "article_id": article_id}


async def delete_article(arguments: dict) -> dict:
    """软删除文章（仅作者或管理员）"""
    ctx = _require_auth()
    article_id = arguments.get("article_id")
    if not article_id:
        raise ValueError("文章ID不能为空")

    async with db_manager.get_session() as db:
        article = await db.scalar(select(Article).where(Article.id == int(article_id)))
        if not article:
            raise ValueError(f"文章 #{article_id} 不存在")
        if article.user != ctx.id and not ctx.is_superuser:
            raise PermissionError("只能删除自己的文章")

        article.status = -1
        article.deleted_at = datetime.utcnow()
        article.updated_at = datetime.utcnow()
        await db.commit()
        return {"success": True, "message": f"文章 #{article_id} 已删除", "article_id": article_id}


async def search_articles(arguments: dict) -> list:
    """搜索文章（所有用户可读）"""
    _require_auth()
    query_text = (arguments.get("query") or "").strip()
    limit = min(arguments.get("limit", 10), 50)
    if not query_text:
        raise ValueError("搜索关键词不能为空")

    try:
        from shared.services.integrations.meilisearch_service import meilisearch_service
        result = await meilisearch_service.search(query=query_text, page=1, per_page=limit)
        if result and 'articles' in result:
            return [{"id": h.get("id"), "title": h.get("title", ""),
                     "excerpt": h.get("excerpt", ""), "slug": h.get("slug", ""),
                     "category_name": h.get("category_name", ""), "author_name": h.get("author_name", "")}
                    for h in result['articles']]
    except Exception:
        pass

    async with db_manager.get_session() as db:
        pattern = f"%{query_text}%"
        articles = (await db.execute(
            select(Article).where(Article.status == 1)
            .where(Article.title.ilike(pattern) | Article.excerpt.ilike(pattern))
            .order_by(Article.views.desc()).limit(limit)
        )).scalars().all()
        return [{"id": a.id, "title": a.title, "excerpt": a.excerpt or "", "slug": a.slug or ""}
                for a in articles]
