"""
Hexo 导入器 - 从 Hexo 站点导入文章
"""
import os
import re
import yaml
from datetime import datetime
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, Body
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return fail(str(e))
    return wrapper


router = APIRouter(tags=["hexo-import"])


def parse_hexo_post(content: str, filename: str = "") -> dict:
    """解析 Hexo Markdown 文件"""
    result = {
        "title": filename.replace(".md", ""),
        "date": None,
        "tags": [],
        "categories": [],
        "content": content,
        "slug": "",
    }
    
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
            result["content"] = fm_match.group(2)
            for key in ["title", "date", "tags", "categories", "slug"]:
                if key in fm:
                    result[key] = fm[key]
        except Exception:
            pass
    
    if isinstance(result["date"], datetime):
        result["date"] = result["date"].isoformat()
    # Handle hexo-style tags
    if isinstance(result.get("tags"), list):
        result["tags"] = [t.get("name", t) if isinstance(t, dict) else t for t in result["tags"]]
    
    return result


@router.post("/parse")
@_catch
async def parse_hexo_file(file: UploadFile = File(...)):
    """解析 Hexo Markdown 文件"""
    content = (await file.read()).decode("utf-8", errors="replace")
    post = parse_hexo_post(content, file.filename or "")
    return ok(data={
        "filename": file.filename,
        "title": post["title"],
        "date": str(post["date"]) if post["date"] else None,
        "tags": post["tags"],
        "categories": post["categories"],
        "word_count": len(post["content"]),
        "preview": post["content"][:500],
    })


@router.post("/import")
@_catch
async def import_hexo_posts(files: list[UploadFile] = File(...),
                              default_author_id: int = Form(1),
                              current_user=Depends(jwt_required),
                              db: AsyncSession = Depends(get_async_db)):
    """批量导入 Hexo 文章"""
    from shared.models.article import Article, ArticleContent
    from datetime import datetime, timezone
    
    imported = 0
    errors = []
    
    for file in files:
        try:
            content = (await file.read()).decode("utf-8", errors="replace")
            post = parse_hexo_post(content, file.filename or "")
            
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            article = Article(
                title=post["title"][:255],
                slug=post["slug"] or post["title"].lower().replace(" ", "-")[:255],
                tags_list=post.get("tags", []),
                category=post["categories"][0] if post.get("categories") else None,
                status=1,
                user=default_author_id,
                is_featured=False,
                is_vip_only=False,
                created_at=now,
                updated_at=now,
            )
            db.add(article)
            await db.flush()
            
            content_obj = ArticleContent(article=article.id, content=post["content"],
                                          created_at=now, updated_at=now)
            db.add(content_obj)
            imported += 1
        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})
    
    await db.commit()
    return ok(data={"imported": imported, "errors": errors, "total": len(files)})
