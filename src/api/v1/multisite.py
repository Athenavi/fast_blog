"""
多站点管理 API
提供站点配置、域名绑定、用户管理和内容同步功能
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.multisite_service import multisite_service
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required, get_current_user
from src.extensions import get_async_db_session as get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/multisite", tags=["multisite"])


# ==================== 站点管理 ====================

@router.post("/sites", summary="创建站点")
async def create_site(
        name: str = Body(..., description="站点名称"),
        slug: str = Body(..., description="站点标识"),
        domain: str = Body(..., description="主域名"),
        description: Optional[str] = Body(None, description="描述"),
        is_default: bool = Body(False, description="是否为默认站点"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建新站点
    
    Args:
        name: 站点名称
        slug: 站点标识
        domain: 主域名
        description: 描述
        is_default: 是否为默认站点
        
    Returns:
        创建的站点
    """
    try:
        # 检查权限（需要admin权限）
        has_permission = await check_admin_permission(db, current_user.id)
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        site = await multisite_service.create_site(
            db=db,
            name=name,
            slug=slug,
            domain=domain,
            description=description,
            is_default=is_default
        )

        return ApiResponse(
            success=True,
            data={
                'id': site.id,
                'name': site.name,
                'slug': site.slug,
                'domain': site.domain,
                'description': site.description,
                'is_default': site.is_default,
                'created_at': site.created_at.isoformat() if site.created_at else None,
            },
            message="Site created successfully"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/sites", summary="获取站点列表")
async def get_sites(
        include_inactive: bool = Query(False, description="是否包含非活动站点"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取所有站点列表
    
    Args:
        include_inactive: 是否包含非活动站点
        
    Returns:
        站点列表
    """
    try:
        sites = await multisite_service.get_all_sites(db, include_inactive)

        sites_list = []
        for site in sites:
            sites_list.append({
                'id': site.id,
                'name': site.name,
                'slug': site.slug,
                'domain': site.domain,
                'description': site.description,
                'logo_url': site.logo_url,
                'favicon_url': site.favicon_url,
                'theme': site.theme,
                'language': site.language,
                'timezone': site.timezone,
                'is_active': site.is_active,
                'is_default': site.is_default,
                'created_at': site.created_at.isoformat() if site.created_at else None,
            })

        return ApiResponse(
            success=True,
            data={
                'sites': sites_list,
                'total': len(sites_list)
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.put("/sites/{site_id}", summary="更新站点配置")
async def update_site(
        site_id: int,
        updates: Dict[str, Any] = Body(..., description="更新字段"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新站点配置
    
    Args:
        site_id: 站点ID
        updates: 更新字段
        
    Returns:
        更新后的站点
    """
    try:
        # 检查权限
        has_permission = await check_admin_permission(db, current_user.id)
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        site = await multisite_service.update_site(db, site_id, updates)

        return ApiResponse(
            success=True,
            data={
                'id': site.id,
                'name': site.name,
                'slug': site.slug,
                'domain': site.domain,
            },
            message="Site updated successfully"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/sites/{site_id}", summary="删除站点")
async def delete_site(
        site_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除站点
    
    Args:
        site_id: 站点ID
        
    Returns:
        删除结果
    """
    try:
        # 检查权限
        has_permission = await check_admin_permission(db, current_user.id)
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        await multisite_service.delete_site(db, site_id)

        return ApiResponse(
            success=True,
            message="Site deleted successfully"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 域名管理 ====================

@router.post("/sites/{site_id}/domains", summary="添加附加域名")
async def add_domain(
        site_id: int,
        domain: str = Body(..., description="域名"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    为站点添加附加域名
    
    Args:
        site_id: 站点ID
        domain: 域名
        
    Returns:
        添加结果
    """
    try:
        # 检查权限
        has_permission = await check_admin_permission(db, current_user.id)
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        await multisite_service.add_domain(db, site_id, domain)

        return ApiResponse(
            success=True,
            message=f"Domain {domain} added successfully"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/sites/{site_id}/domains", summary="移除附加域名")
async def remove_domain(
        site_id: int,
        domain: str = Body(..., description="域名"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    从站点移除附加域名
    
    Args:
        site_id: 站点ID
        domain: 域名
        
    Returns:
        移除结果
    """
    try:
        # 检查权限
        has_permission = await check_admin_permission(db, current_user.id)
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        await multisite_service.remove_domain(db, site_id, domain)

        return ApiResponse(
            success=True,
            message=f"Domain {domain} removed successfully"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 用户管理 ====================

@router.post("/sites/{site_id}/users", summary="添加用户到站点")
async def add_user_to_site(
        site_id: int,
        user_id: int = Body(..., description="用户ID"),
        role: str = Body("subscriber", description="角色"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    添加用户到站点（共享用户体系）
    
    Args:
        site_id: 站点ID
        user_id: 用户ID
        role: 在该站点的角色
        
    Returns:
        添加结果
    """
    try:
        # 检查权限
        has_permission = await check_admin_permission(db, current_user.id)
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        await multisite_service.add_user_to_site(db, site_id, user_id, role)

        return ApiResponse(
            success=True,
            message=f"User {user_id} added to site {site_id}"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/sites/{site_id}/users/{user_id}", summary="从站点移除用户")
async def remove_user_from_site(
        site_id: int,
        user_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    从站点移除用户
    
    Args:
        site_id: 站点ID
        user_id: 用户ID
        
    Returns:
        移除结果
    """
    try:
        # 检查权限
        has_permission = await check_admin_permission(db, current_user.id)
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        await multisite_service.remove_user_from_site(db, site_id, user_id)

        return ApiResponse(
            success=True,
            message=f"User {user_id} removed from site {site_id}"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/users/{user_id}/sites", summary="获取用户的站点列表")
async def get_user_sites(
        user_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户所属的所有站点
    
    Args:
        user_id: 用户ID
        
    Returns:
        站点列表
    """
    try:
        sites = await multisite_service.get_user_sites(db, user_id)

        return ApiResponse(
            success=True,
            data={
                'sites': sites,
                'total': len(sites)
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 内容同步 ====================

@router.post("/sync", summary="同步内容到其他站点")
async def sync_content(
        source_site_id: int = Body(..., description="源站点ID"),
        target_site_id: int = Body(..., description="目标站点ID"),
        content_type: str = Body(..., description="内容类型 (article/page)"),
        source_content_id: int = Body(..., description="源内容ID"),
        sync_mode: str = Body("manual", description="同步模式 (manual/auto)"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    同步内容到其他站点
    
    Args:
        source_site_id: 源站点ID
        target_site_id: 目标站点ID
        content_type: 内容类型
        source_content_id: 源内容ID
        sync_mode: 同步模式
        
    Returns:
        同步结果
    """
    try:
        # 检查权限
        has_permission = await check_admin_permission(db, current_user.id)
        if not has_permission:
            return ApiResponse(success=False, error="Insufficient permissions")

        mapping = await multisite_service.sync_content(
            db=db,
            source_site_id=source_site_id,
            target_site_id=target_site_id,
            content_type=content_type,
            source_content_id=source_content_id,
            sync_mode=sync_mode
        )

        return ApiResponse(
            success=True,
            data={
                'id': mapping.id,
                'source_site_id': mapping.source_site_id,
                'target_site_id': mapping.target_site_id,
                'content_type': mapping.content_type,
                'source_content_id': mapping.source_content_id,
                'target_content_id': mapping.target_content_id,
                'sync_mode': mapping.sync_mode,
                'last_synced_at': mapping.last_synced_at.isoformat() if mapping.last_synced_at else None,
            },
            message="Content synced successfully"
        )

    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 辅助函数 ====================

async def check_admin_permission(db, user_id: int) -> bool:
    """
    检查用户是否有管理员权限
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        是否有权限
    """
    try:
        from shared.services.rbac_service import rbac_service
        return await rbac_service.check_permission(db, user_id, 'settings:update')
    except:
        return False
