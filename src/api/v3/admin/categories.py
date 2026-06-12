"""
V3 分类管理 API

权限要求:
  GET    /categories          → category:view
  POST   /categories          → category:create
  PUT    /categories/{id}     → category:edit
  DELETE /categories/{id}     → category:delete
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.category import Category
from shared.models.article import Article
from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db
from src.api.v3._permission import Permission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-categories"])


@router.get("/categories", summary="分类列表")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("category:view")),
):
    result = await db.execute(
        select(Category).order_by(Category.sort_order, Category.name)
    )
    categories = result.scalars().all()
    return ApiResponse(success=True, data={
        "categories": [_cat_dict(c) for c in categories],
    })


@router.post("/categories", summary="创建分类", status_code=201)
async def create_category(
    name: str = Body(...),
    slug: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    parent_id: Optional[int] = Body(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("category:create")),
):
    now = datetime.now(timezone.utc)
    cat = Category(
        name=name,
        slug=slug or name.lower().replace(" ", "-"),
        description=description,
        parent_id=parent_id,
        sort_order=0,
        created_at=now,
        updated_at=now,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return ApiResponse(success=True, data=_cat_dict(cat), message="分类创建成功")


@router.put("/categories/{category_id}", summary="编辑分类")
async def update_category(
    category_id: int,
    name: Optional[str] = Body(None),
    slug: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    sort_order: Optional[int] = Body(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("category:edit")),
):
    cat = await db.get(Category, category_id)
    if not cat:
        return ApiResponse(success=False, error="分类不存在")

    if name is not None: cat.name = name
    if slug is not None: cat.slug = slug
    if description is not None: cat.description = description
    if sort_order is not None: cat.sort_order = sort_order
    cat.updated_at = datetime.now(timezone.utc)

    await db.commit()
    return ApiResponse(success=True, message="分类已更新")


@router.delete("/categories/{category_id}", summary="删除分类")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("category:delete")),
):
    cat = await db.get(Category, category_id)
    if not cat:
        return ApiResponse(success=False, error="分类不存在")

    # 清除文章的该分类引用
    await db.execute(
        Article.__table__.update().where(Article.category == category_id).values(category=None)
    )
    await db.delete(cat)
    await db.commit()
    return ApiResponse(success=True, message="分类已删除")


def _cat_dict(c: Category) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "slug": c.slug,
        "description": c.description,
        "parent_id": c.parent_id,
        "sort_order": c.sort_order,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
