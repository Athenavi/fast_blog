"""
页面构建器 API 路由
提供页面的创建、保存、加载、发布和删除功能
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.page_builder import PageBuilder
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from shared.models.user import User
from src.utils.database.main import get_async_session

router = APIRouter(prefix="/page-builder", tags=["Page Builder"])


class PageCreateRequest(BaseModel):
    """创建页面请求"""
    title: str
    slug: str
    blocks_data: list = []  # JSON 数组
    template_name: Optional[str] = None
    is_published: bool = False


class PageUpdateRequest(BaseModel):
    """更新页面请求"""
    title: Optional[str] = None
    blocks_data: Optional[list] = None
    template_name: Optional[str] = None
    is_published: Optional[bool] = None


class PageResponse(BaseModel):
    """页面响应"""
    id: int
    title: str
    slug: str
    blocks_data: list
    template_name: Optional[str] = None
    is_published: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.post("/pages", response_model=PageResponse)
async def create_page(
        req: PageCreateRequest,
        current_user: User = Depends(jwt_required)
):
    """P2-1: 创建新页面
    
    Args:
        req: 页面创建请求
        current_user: 当前登录用户
        
    Returns:
        创建的页面对象
    """
    async for db in get_async_session():
        # 检查 slug 是否已存在
        existing = await db.execute(
            select(PageBuilder).where(PageBuilder.slug == req.slug)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Slug '{req.slug}' 已存在")

        # 创建新页面
        new_page = PageBuilder(
            title=req.title,
            slug=req.slug,
            blocks_data=str(req.blocks_data),  # 存储为 JSON 字符串
            template_name=req.template_name,
            is_published=req.is_published,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_page)
        await db.commit()
        await db.refresh(new_page)

        # 解析 blocks_data 为列表返回
        import json
        try:
            blocks = json.loads(new_page.blocks_data)
        except:
            blocks = []

        return PageResponse(
            id=new_page.id,
            title=new_page.title,
            slug=new_page.slug,
            blocks_data=blocks,
            template_name=new_page.template_name,
            is_published=new_page.is_published,
            created_at=new_page.created_at.isoformat() if new_page.created_at else None,
            updated_at=new_page.updated_at.isoformat() if new_page.updated_at else None
        )


@router.get("/pages", response_model=List[PageResponse])
async def list_pages(
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        published_only: bool = Query(False),
        current_user: User = Depends(jwt_required)
):
    """P2-1: 获取页面列表
    
    Args:
        skip: 跳过数量
        limit: 限制数量
        published_only: 仅返回已发布页面
        
    Returns:
        页面列表
    """
    async for db in get_async_session():
        query = select(PageBuilder)

        if published_only:
            query = query.where(PageBuilder.is_published == True)

        query = query.order_by(desc(PageBuilder.created_at)).offset(skip).limit(limit)

        result = await db.execute(query)
        pages = result.scalars().all()

        import json
        response_list = []
        for page in pages:
            try:
                blocks = json.loads(page.blocks_data)
            except:
                blocks = []

            response_list.append(PageResponse(
                id=page.id,
                title=page.title,
                slug=page.slug,
                blocks_data=blocks,
                template_name=page.template_name,
                is_published=page.is_published,
                created_at=page.created_at.isoformat() if page.created_at else None,
                updated_at=page.updated_at.isoformat() if page.updated_at else None
            ))

        return response_list


@router.get("/pages/{page_id}", response_model=PageResponse)
async def get_page(
        page_id: int,
        current_user: User = Depends(jwt_required)
):
    """P2-1: 获取单个页面详情
    
    Args:
        page_id: 页面 ID
        
    Returns:
        页面对象
    """
    async for db in get_async_session():
        result = await db.execute(
            select(PageBuilder).where(PageBuilder.id == page_id)
        )
        page = result.scalar_one_or_none()

        if not page:
            raise HTTPException(status_code=404, detail="页面不存在")

        import json
        try:
            blocks = json.loads(page.blocks_data)
        except:
            blocks = []

        return PageResponse(
            id=page.id,
            title=page.title,
            slug=page.slug,
            blocks_data=blocks,
            template_name=page.template_name,
            is_published=page.is_published,
            created_at=page.created_at.isoformat() if page.created_at else None,
            updated_at=page.updated_at.isoformat() if page.updated_at else None
        )


@router.put("/pages/{page_id}", response_model=PageResponse)
async def update_page(
        page_id: int,
        req: PageUpdateRequest,
        current_user: User = Depends(jwt_required)
):
    """P2-1: 更新页面
    
    Args:
        page_id: 页面 ID
        req: 更新请求
        
    Returns:
        更新后的页面对象
    """
    async for db in get_async_session():
        result = await db.execute(
            select(PageBuilder).where(PageBuilder.id == page_id)
        )
        page = result.scalar_one_or_none()

        if not page:
            raise HTTPException(status_code=404, detail="页面不存在")

        # 更新字段
        if req.title is not None:
            page.title = req.title
        if req.blocks_data is not None:
            page.blocks_data = str(req.blocks_data)
        if req.template_name is not None:
            page.template_name = req.template_name
        if req.is_published is not None:
            page.is_published = req.is_published

        page.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(page)

        import json
        try:
            blocks = json.loads(page.blocks_data)
        except:
            blocks = []

        return PageResponse(
            id=page.id,
            title=page.title,
            slug=page.slug,
            blocks_data=blocks,
            template_name=page.template_name,
            is_published=page.is_published,
            created_at=page.created_at.isoformat() if page.created_at else None,
            updated_at=page.updated_at.isoformat() if page.updated_at else None
        )


@router.delete("/pages/{page_id}")
async def delete_page(
        page_id: int,
        current_user: User = Depends(jwt_required)
):
    """P2-1: 删除页面
    
    Args:
        page_id: 页面 ID
        
    Returns:
        删除结果
    """
    async for db in get_async_session():
        result = await db.execute(
            select(PageBuilder).where(PageBuilder.id == page_id)
        )
        page = result.scalar_one_or_none()

        if not page:
            raise HTTPException(status_code=404, detail="页面不存在")

        await db.delete(page)
        await db.commit()

        return {"success": True, "message": "页面已删除"}


@router.post("/pages/{page_id}/publish")
async def publish_page(
        page_id: int,
        current_user: User = Depends(jwt_required)
):
    """P2-1: 发布页面
    
    Args:
        page_id: 页面 ID
        
    Returns:
        发布结果
    """
    async for db in get_async_session():
        result = await db.execute(
            select(PageBuilder).where(PageBuilder.id == page_id)
        )
        page = result.scalar_one_or_none()

        if not page:
            raise HTTPException(status_code=404, detail="页面不存在")

        page.is_published = True
        page.updated_at = datetime.utcnow()

        await db.commit()

        return {"success": True, "message": "页面已发布"}


@router.post("/pages/{page_id}/unpublish")
async def unpublish_page(
        page_id: int,
        current_user: User = Depends(jwt_required)
):
    """P2-1: 取消发布页面
    
    Args:
        page_id: 页面 ID
        
    Returns:
        取消发布结果
    """
    async for db in get_async_session():
        result = await db.execute(
            select(PageBuilder).where(PageBuilder.id == page_id)
        )
        page = result.scalar_one_or_none()

        if not page:
            raise HTTPException(status_code=404, detail="页面不存在")

        page.is_published = False
        page.updated_at = datetime.utcnow()

        await db.commit()

        return {"success": True, "message": "页面已取消发布"}


@router.get("/pages/slug/{slug}", response_model=PageResponse)
async def get_page_by_slug(slug: str):
    """P2-1: 通过 slug 获取公开页面（无需认证）
    
    Args:
        slug: 页面路径标识
        
    Returns:
        页面对象（仅已发布的）
    """
    async for db in get_async_session():
        result = await db.execute(
            select(PageBuilder).where(
                (PageBuilder.slug == slug) &
                (PageBuilder.is_published == True)
            )
        )
        page = result.scalar_one_or_none()

        if not page:
            raise HTTPException(status_code=404, detail="页面不存在或未发布")

        import json
        try:
            blocks = json.loads(page.blocks_data)
        except:
            blocks = []

        return PageResponse(
            id=page.id,
            title=page.title,
            slug=page.slug,
            blocks_data=blocks,
            template_name=page.template_name,
            is_published=page.is_published,
            created_at=page.created_at.isoformat() if page.created_at else None,
            updated_at=page.updated_at.isoformat() if page.updated_at else None
        )
