"""
自定义文章类型内容管理服务
提供 CustomPostContent 的 CRUD 操作和查询
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.content import CustomPostContent, CustomPostType
from src.unified_logger import default_logger as logger


async def get_post_type_by_slug(db: AsyncSession, slug: str) -> Optional[CustomPostType]:
    """根据 slug 获取文章类型"""
    result = await db.execute(
        select(CustomPostType).where(CustomPostType.slug == slug, CustomPostType.is_active == True)
    )
    return result.scalar_one_or_none()


async def create_custom_post_content(
    db: AsyncSession,
    post_type_id: int,
    title: str,
    slug: str,
    content: str = "",
    excerpt: str = "",
    meta: Optional[Dict[str, Any]] = None,
    author_id: int = 0,
    status: int = 0,
    password: Optional[str] = None,
) -> Optional[CustomPostContent]:
    """创建自定义文章内容"""
    try:
        now = datetime.now(timezone.utc)

        post = CustomPostContent(
            post_type_id=post_type_id,
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            meta=json.dumps(meta) if meta else None,
            author_id=author_id,
            status=status,
            password=password,
            published_at=now if status == 1 else None,
            created_at=now,
            updated_at=now,
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        return post

    except Exception as e:
        await db.rollback()
        logger.error(f"创建自定义内容失败: {e}", exc_info=True)
        return None


async def get_custom_post_content(
    db: AsyncSession,
    content_id: int,
    post_type_id: Optional[int] = None,
) -> Optional[CustomPostContent]:
    """获取自定义文章内容"""
    query = select(CustomPostContent).where(CustomPostContent.id == content_id)
    if post_type_id:
        query = query.where(CustomPostContent.post_type_id == post_type_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_custom_post_content(
    db: AsyncSession,
    content_id: int,
    **kwargs,
) -> bool:
    """更新自定义文章内容"""
    try:
        result = await db.execute(
            select(CustomPostContent).where(CustomPostContent.id == content_id)
        )
        post = result.scalar_one_or_none()
        if not post:
            return False

        # 只允许更新已知字段
        allowed = {'title', 'slug', 'content', 'excerpt', 'meta', 'status', 'is_featured', 'password'}
        for key, value in kwargs.items():
            if key in allowed and value is not None:
                if key == 'meta' and isinstance(value, dict):
                    setattr(post, key, json.dumps(value))
                else:
                    setattr(post, key, value)

        post.updated_at = datetime.now(timezone.utc)
        if kwargs.get('status') == 1 and not post.published_at:
            post.published_at = datetime.now(timezone.utc)

        await db.commit()
        return True

    except Exception as e:
        await db.rollback()
        logger.error(f"更新自定义内容失败: {e}", exc_info=True)
        return False


async def delete_custom_post_content(db: AsyncSession, content_id: int) -> bool:
    """删除自定义文章内容"""
    try:
        result = await db.execute(
            select(CustomPostContent).where(CustomPostContent.id == content_id)
        )
        post = result.scalar_one_or_none()
        if not post:
            return False

        await db.delete(post)
        await db.commit()
        return True

    except Exception as e:
        await db.rollback()
        logger.error(f"删除自定义内容失败: {e}", exc_info=True)
        return False


async def list_custom_post_contents(
    db: AsyncSession,
    post_type_id: int,
    page: int = 1,
    per_page: int = 20,
    status: Optional[int] = None,
) -> Dict[str, Any]:
    """分页列出自定义文章内容"""
    query = select(CustomPostContent).where(CustomPostContent.post_type_id == post_type_id)

    if status is not None:
        query = query.where(CustomPostContent.status == status)

    # 总数
    count_query = select(func.count(CustomPostContent.id)).where(
        CustomPostContent.post_type_id == post_type_id
    )
    if status is not None:
        count_query = count_query.where(CustomPostContent.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 分页
    offset = (page - 1) * per_page
    total_pages = max(1, (total + per_page - 1) // per_page)
    query = query.order_by(CustomPostContent.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    posts = result.scalars().all()

    return {
        "success": True,
        "posts": [p.to_dict() for p in posts],
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


__all__ = [
    'get_post_type_by_slug',
    'create_custom_post_content',
    'get_custom_post_content',
    'update_custom_post_content',
    'delete_custom_post_content',
    'list_custom_post_contents',
]
