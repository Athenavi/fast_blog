"""
多站点管理 API
提供站点配置、域名绑定、用户管理和内容同步功能
"""
from functools import wraps
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.system.multisite_service import multisite_service
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["multisite"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            return fail(str(e))
    return wrapper


# ==================== 站点管理 ====================

@router.post("", summary="创建站点")
@_catch
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
    # 检查权限（需要admin权限）
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    site = await multisite_service.create_site(
        db=db,
        name=name,
        slug=slug,
        domain=domain,
        description=description,
        is_default=is_default
    )

    return ok(
        data={
            'id': site.id,
            'name': site.name,
            'slug': site.slug,
            'domain': site.domain,
            'description': site.description,
            'is_default': site.is_default,
            'created_at': site.created_at.isoformat() if site.created_at else None,
        },
        msg="Site created successfully"
    )


@router.get("", summary="获取站点列表")
@_catch
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

    return ok(data={
        'sites': sites_list,
        'total': len(sites_list)
    })


@router.put("/{site_id}", summary="更新站点配置")
@_catch
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
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    site = await multisite_service.update_site(db, site_id, updates)

    return ok(
        data={
            'id': site.id,
            'name': site.name,
            'slug': site.slug,
            'domain': site.domain,
        },
        msg="Site updated successfully"
    )


@router.delete("/{site_id}", summary="删除站点")
@_catch
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
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    await multisite_service.delete_site(db, site_id)

    return ok(msg="Site deleted successfully")


# ==================== 域名管理 ====================

@router.post("/domains", summary="添加附加域名")
@_catch
async def add_domain(
        site_id: int,
        domain: str = Body(..., description="域名"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """为站点添加附加域名"""
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    await multisite_service.add_domain(db, site_id, domain)

    return ok(msg=f"Domain {domain} added successfully")


@router.delete("/domains", summary="移除附加域名")
@_catch
async def remove_domain(
        site_id: int,
        domain: str = Body(..., description="域名"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """从站点移除附加域名"""
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    await multisite_service.remove_domain(db, site_id, domain)

    return ok(msg=f"Domain {domain} removed successfully")


# ==================== 用户管理 ====================

@router.post("/users", summary="添加用户到站点")
@_catch
async def add_user_to_site(
        site_id: int,
        user_id: int = Body(..., description="用户ID"),
        role: str = Body("subscriber", description="角色"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """添加用户到站点（共享用户体系）"""
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    await multisite_service.add_user_to_site(db, site_id, user_id, role)

    return ok(msg=f"User {user_id} added to site {site_id}")


@router.delete("/users/{user_id}", summary="从站点移除用户")
@_catch
async def remove_user_from_site(
        site_id: int,
        user_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """从站点移除用户"""
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    await multisite_service.remove_user_from_site(db, site_id, user_id)

    return ok(msg=f"User {user_id} removed from site {site_id}")


@router.get("/users/{user_id}/sites", summary="获取用户的站点列表")
@_catch
async def get_user_sites(
        user_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取用户所属的所有站点"""
    sites = await multisite_service.get_user_sites(db, user_id)

    return ok(data={
        'sites': sites,
        'total': len(sites)
    })


# ==================== 内容同步 ====================

@router.post("/sync", summary="同步内容到其他站点")
@_catch
async def sync_content(
        source_site_id: int = Body(..., description="源站点ID"),
        target_site_id: int = Body(..., description="目标站点ID"),
        content_type: str = Body(..., description="内容类型 (article/page)"),
        source_content_id: int = Body(..., description="源内容ID"),
        sync_mode: str = Body("manual", description="同步模式 (manual/auto)"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """同步内容到其他站点"""
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    mapping = await multisite_service.sync_content(
        db=db,
        source_site_id=source_site_id,
        target_site_id=target_site_id,
        content_type=content_type,
        source_content_id=source_content_id,
        sync_mode=sync_mode
    )

    return ok(
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
        msg="Content synced successfully"
    )


@router.get("/{site_id}", summary="获取站点详情")
@_catch
async def get_site_detail(
        site_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取站点详细信息"""
    from shared.models.site import Site
    from sqlalchemy import select

    stmt = select(Site).where(Site.id == site_id)
    result = await db.execute(stmt)
    site = result.scalar_one_or_none()

    if not site:
        return fail("Site not found")

    # 解析附加域名
    additional_domains = []
    if site.additional_domains:
        try:
            import json
            additional_domains = json.loads(site.additional_domains)
        except:
            pass

    # 解析设置
    settings = {}
    if site.settings:
        try:
            import json
            settings = json.loads(site.settings)
        except:
            pass

    return ok(data={
        'id': site.id,
        'name': site.name,
        'slug': site.slug,
        'domain': site.domain,
        'additional_domains': additional_domains,
        'description': site.description,
        'logo_url': site.logo_url,
        'favicon_url': site.favicon_url,
        'theme': site.theme,
        'language': site.language,
        'timezone': site.timezone,
        'settings': settings,
        'is_active': site.is_active,
        'is_default': site.is_default,
        'created_at': site.created_at.isoformat() if site.created_at else None,
        'updated_at': site.updated_at.isoformat() if site.updated_at else None,
    })


@router.get("/{site_id}/users", summary="获取站点的用户列表")
@_catch
async def get_site_users(
        site_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取站点的用户列表"""
    from shared.models.site_user import SiteUser
    from shared.models.user import User
    from sqlalchemy import select

    stmt = (
        select(User, SiteUser)
        .join(SiteUser, User.id == SiteUser.user_id)
        .where(
            SiteUser.site_id == site_id,
            SiteUser.is_active == True
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    users_list = []
    for user, site_user in rows:
        users_list.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': site_user.role,
            'joined_at': site_user.joined_at.isoformat() if site_user.joined_at else None,
        })

    return ok(data={
        'users': users_list,
        'total': len(users_list)
    })


@router.put("/{site_id}/users/{user_id}/role", summary="更新用户在站点的角色")
@_catch
async def update_user_role(
        site_id: int,
        user_id: int,
        role: str = Body(..., description="新角色"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """更新用户在站点的角色"""
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    from shared.models.site_user import SiteUser
    from sqlalchemy import select

    stmt = select(SiteUser).where(
        SiteUser.site_id == site_id,
        SiteUser.user_id == user_id
    )
    result = await db.execute(stmt)
    site_user = result.scalar_one_or_none()

    if not site_user:
        return fail("User not found in this site")

    site_user.role = role
    await db.commit()

    return ok(msg=f"User role updated to {role}")


@router.get("/{site_id}/content-mappings", summary="获取站点的内容映射")
@_catch
async def get_content_mappings(
        site_id: int,
        direction: str = Query("outgoing", description="方向（outgoing/incoming）"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取站点的内容映射记录"""
    from shared.models.content_mapping import ContentMapping
    from sqlalchemy import select

    if direction == "outgoing":
        stmt = select(ContentMapping).where(
            ContentMapping.source_site_id == site_id
        ).order_by(ContentMapping.created_at.desc())
    else:
        stmt = select(ContentMapping).where(
            ContentMapping.target_site_id == site_id
        ).order_by(ContentMapping.created_at.desc())

    result = await db.execute(stmt)
    mappings = result.scalars().all()

    mappings_list = []
    for mapping in mappings:
        mappings_list.append({
            'id': mapping.id,
            'source_site_id': mapping.source_site_id,
            'target_site_id': mapping.target_site_id,
            'content_type': mapping.content_type,
            'source_content_id': mapping.source_content_id,
            'target_content_id': mapping.target_content_id,
            'sync_mode': mapping.sync_mode,
            'last_synced_at': mapping.last_synced_at.isoformat() if mapping.last_synced_at else None,
            'created_at': mapping.created_at.isoformat() if mapping.created_at else None,
        })

    return ok(data={
        'mappings': mappings_list,
        'total': len(mappings_list)
    })


# ==================== 辅助函数 ====================

async def check_admin_permission(db, user_id: int) -> bool:
    """
    检查用户是否有管理员权限
    """
    try:
        from shared.services.security.rbac_service import rbac_service
        return await rbac_service.check_permission(db, user_id, 'settings:update')
    except:
        return False
