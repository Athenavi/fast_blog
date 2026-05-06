"""
多站点支持 - 站点管理 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.site import Site
from shared.models.user import User
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/sites", tags=["sites"])


class SiteCreateRequest(BaseModel):
    """创建站点请求"""
    name: str
    slug: str
    domain: Optional[str] = None
    path: Optional[str] = "/"
    theme: Optional[str] = "default"
    language: Optional[str] = "zh-CN"
    timezone: Optional[str] = "Asia/Shanghai"
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    admin_user_id: Optional[int] = None
    settings: Optional[dict] = {}


class SiteUpdateRequest(BaseModel):
    """更新站点请求"""
    name: Optional[str] = None
    domain: Optional[str] = None
    path: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    admin_user_id: Optional[int] = None
    settings: Optional[dict] = None


@router.get("", summary="列出所有站点")
async def list_sites(
        request: Request,
        page: int = 1,
        per_page: int = 20,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取站点列表（需要管理员权限）"""
    # 检查权限：仅超级管理员可以查看所有站点
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Superuser required."
        )

    offset = (page - 1) * per_page

    # 查询总数
    count_stmt = select(func.count(Site.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # 查询数据
    stmt = select(Site).order_by(Site.id.desc()).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    sites = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": site.id,
                "name": site.name,
                "slug": site.slug,
                "domain": site.domain,
                "path": site.path,
                "is_active": site.is_active,
                "is_default": site.is_default,
                "theme": site.theme,
                "language": site.language,
                "created_at": site.created_at.isoformat() if site.created_at else None,
            }
            for site in sites
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }
    }


@router.post("", summary="创建新站点")
async def create_site(
        request: Request,
        data: SiteCreateRequest,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """创建新站点（需要超级管理员权限）"""
    # 检查权限：仅超级管理员可以创建站点
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Superuser required."
        )

    # 检查 slug 是否已存在
    stmt = select(Site).where(Site.slug == data.slug)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Site slug '{data.slug}' already exists"
        )

    # 如果设置为默认站点，取消其他站点的默认状态
    if data.settings and data.settings.get('is_default'):
        stmt = select(Site).where(Site.is_default == True)
        result = await db.execute(stmt)
        default_sites = result.scalars().all()
        for site in default_sites:
            site.is_default = False

    # 创建新站点
    new_site = Site(
        name=data.name,
        slug=data.slug,
        domain=data.domain,
        path=data.path,
        theme=data.theme,
        language=data.language,
        timezone=data.timezone,
        title=data.title,
        description=data.description,
        keywords=data.keywords,
        admin_user_id=data.admin_user_id,
        settings=data.settings or {},
        is_active=True,
        is_default=data.settings.get('is_default', False) if data.settings else False,
    )

    db.add(new_site)
    await db.commit()
    await db.refresh(new_site)

    return {
        "success": True,
        "message": "Site created successfully",
        "data": {
            "id": new_site.id,
            "name": new_site.name,
            "slug": new_site.slug,
        }
    }


@router.get("/{site_id}", summary="获取站点详情")
async def get_site(
        site_id: int,
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取单个站点详情"""
    stmt = select(Site).where(Site.id == site_id)
    result = await db.execute(stmt)
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )

    return {
        "success": True,
        "data": {
            "id": site.id,
            "name": site.name,
            "slug": site.slug,
            "domain": site.domain,
            "path": site.path,
            "is_active": site.is_active,
            "is_default": site.is_default,
            "theme": site.theme,
            "language": site.language,
            "timezone": site.timezone,
            "title": site.title,
            "description": site.description,
            "keywords": site.keywords,
            "admin_user_id": site.admin_user_id,
            "settings": site.settings,
            "full_url": site.full_url,
            "created_at": site.created_at.isoformat() if site.created_at else None,
            "updated_at": site.updated_at.isoformat() if site.updated_at else None,
        }
    }


@router.put("/{site_id}", summary="更新站点")
async def update_site(
        site_id: int,
        request: Request,
        data: SiteUpdateRequest,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """更新站点信息"""
    stmt = select(Site).where(Site.id == site_id)
    result = await db.execute(stmt)
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )

    # 更新字段
    update_data = data.dict(exclude_unset=True)

    # 如果设置为默认站点，取消其他站点的默认状态
    if update_data.get('is_default'):
        stmt = select(Site).where(Site.is_default == True, Site.id != site_id)
        result = await db.execute(stmt)
        default_sites = result.scalars().all()
        for s in default_sites:
            s.is_default = False

    for key, value in update_data.items():
        if hasattr(site, key):
            setattr(site, key, value)

    await db.commit()
    await db.refresh(site)

    return {
        "success": True,
        "message": "Site updated successfully",
        "data": {
            "id": site.id,
            "name": site.name,
        }
    }


@router.delete("/{site_id}", summary="删除站点")
async def delete_site(
        site_id: int,
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """删除站点（软删除，标记为非激活）"""
    stmt = select(Site).where(Site.id == site_id)
    result = await db.execute(stmt)
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )

    # 不允许删除默认站点
    if site.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default site"
        )

    # 软删除：标记为非激活
    site.is_active = False
    await db.commit()

    return {
        "success": True,
        "message": "Site deactivated successfully"
    }


@router.get("/{site_id}/stats", summary="获取站点统计")
async def get_site_stats(
        site_id: int,
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取站点统计数据"""
    from shared.models.article import Article
    from shared.models.category import Category

    stmt = select(Site).where(Site.id == site_id)
    result = await db.execute(stmt)
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )

    # 统计文章数量
    article_stmt = select(func.count(Article.id))
    article_result = await db.execute(article_stmt)
    article_count = article_result.scalar()

    # 统计分类数量
    category_stmt = select(func.count(Category.id))
    category_result = await db.execute(category_stmt)
    category_count = category_result.scalar()

    return {
        "success": True,
        "data": {
            "site_id": site_id,
            "site_name": site.name,
            "articles": article_count,
            "categories": category_count,
            "created_at": site.created_at.isoformat() if site.created_at else None,
        }
    }


@router.get("/{site_id}/quota", summary="获取站点配额")
async def get_site_quota(
        site_id: int,
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取站点配额信息（需要管理员权限）"""
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Superuser required."
        )

    from shared.services.site_quota_service import create_site_quota_service

    try:
        service = create_site_quota_service(db)
        quota_info = await service.get_site_quota(site_id)

        return {
            "success": True,
            "data": quota_info
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/{site_id}/quota", summary="更新站点配额")
async def update_site_quota(
        site_id: int,
        request: Request,
        quotas: dict,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """更新站点配额（需要超级管理员权限）"""
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Superuser required."
        )

    from shared.services.site_quota_service import create_site_quota_service

    try:
        service = create_site_quota_service(db)
        result = await service.update_site_quota(site_id, quotas)

        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
