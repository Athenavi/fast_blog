"""
Jekyll 导入器 - 从 Jekyll 站点导入文章
"""
import os
import re
import yaml
import json
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


router = APIRouter(tags=["jekyll-import"])


def parse_jekyll_post(content: str, filename: str = "") -> dict:
    """解析 Jekyll Markdown 文件（含 front matter）"""
    result = {
        "title": filename.replace(".md", "").replace(".markdown", ""),
        "date": None,
        "tags": [],
        "categories": [],
        "content": content,
        "excerpt": "",
        "slug": "",
        "layout": "post",
        "published": True,
    }
    
    # Parse YAML front matter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
            result["content"] = fm_match.group(2)
            for key in ["title", "date", "tags", "categories", "slug", "layout", "excerpt", "published"]:
                if key in fm:
                    result[key] = fm[key]
        except Exception:
            pass
    
    # Parse date from filename (Jekyll convention: YYYY-MM-DD-title.md)
    if not result["date"]:
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})-', filename)
        if date_match:
            try:
                result["date"] = datetime.strptime(date_match.group(1), "%Y-%m-%d").isoformat()
            except Exception:
                pass
    
    if isinstance(result["date"], datetime):
        result["date"] = result["date"].isoformat()
    
    return result


@router.post("/parse")
@_catch
async def parse_jekyll_file(file: UploadFile = File(...)):
    """解析 Jekyll Markdown 文件"""
    content = (await file.read()).decode("utf-8", errors="replace")
    post = parse_jekyll_post(content, file.filename or "")
    return ok(data={
        "filename": file.filename,
        "title": post["title"],
        "date": str(post["date"]) if post["date"] else None,
        "tags": post["tags"],
        "categories": post["categories"],
        "word_count": len(post["content"]),
        "has_front_matter": "---" in content[:200],
        "preview": post["content"][:500],
    })


@router.post("/import")
@_catch
async def import_jekyll_posts(files: list[UploadFile] = File(...),
                               default_author_id: int = Form(1),
                               current_user=Depends(jwt_required),
                               db: AsyncSession = Depends(get_async_db)):
    """批量导入 Jekyll 文章"""
    from shared.models.article import Article, ArticleContent
    from datetime import datetime, timezone
    
    imported = 0
    errors = []
    
    for file in files:
        try:
            content = (await file.read()).decode("utf-8", errors="replace")
            post = parse_jekyll_post(content, file.filename or "")
            
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            article = Article(
                title=post["title"][:255],
                slug=post["slug"] or post["title"].lower().replace(" ", "-")[:255],
                excerpt=post["excerpt"][:500] if post["excerpt"] else "",
                tags_list=post["tags"],
                category=post["categories"][0] if post["categories"] else None,
                status=1 if post.get("published", True) else 0,
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
