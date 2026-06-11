"""
百度统计集成 API

提供百度统计配置管理和追踪代码生成功能
"""
from functools import wraps
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.analytics.baidu_analytics_service import baidu_analytics_service
from src.api.v2._helpers import ok, fail
from src.api.v2.system.multisite import check_admin_permission
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["baidu-analytics"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            return fail(str(e))
    return wrapper


@router.get("/config", summary="获取百度统计配置")
@_catch
async def get_baidu_config(
        site_id: Optional[int] = Query(None, description="站点 ID（为空则获取全局配置）"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取百度统计配置
    
    Args:
        site_id: 站点 ID（可选）
        
    Returns:
        百度统计配置
    """
    config = await baidu_analytics_service.get_config(db, site_id)

    if not config:
        return ok(
            data=None,
            msg="No Baidu Analytics configuration found"
        )

    return ok(
        data={
            'id': config.id,
            'site_id': config.site_id,
            'site_token': config.site_token,
            'enable_tracking': config.enable_tracking,
            'enable_data_sync': config.enable_data_sync,
            'is_active': config.is_active,
            'created_at': config.created_at.isoformat() if config.created_at else None,
            'updated_at': config.updated_at.isoformat() if config.updated_at else None,
        }
    )


@router.post("/config", summary="创建百度统计配置")
@_catch
async def create_baidu_config(
        site_token: str = Body(..., description="百度统计 Site Token"),
        api_key: Optional[str] = Body(None, description="百度统计 API Key"),
        site_id: Optional[int] = Body(None, description="站点 ID（可选）"),
        enable_tracking: bool = Body(True, description="是否启用追踪"),
        enable_data_sync: bool = Body(False, description="是否启用数据同步"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建百度统计配置
    
    Returns:
        创建的配置
    """
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    config = await baidu_analytics_service.create_config(
        db=db,
        site_token=site_token,
        api_key=api_key,
        site_id=site_id,
        enable_tracking=enable_tracking,
        enable_data_sync=enable_data_sync,
    )

    return ok(
        data={
            'id': config.id,
            'site_token': config.site_token,
        },
        msg="Baidu Analytics configuration created successfully"
    )


@router.put("/config/{config_id}", summary="更新百度统计配置")
@_catch
async def update_baidu_config(
        config_id: int,
        updates: Dict[str, Any] = Body(..., description="更新字段"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新百度统计配置
    
    Args:
        config_id: 配置 ID
        updates: 更新字段
        
    Returns:
        更新后的配置
    """
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    config = await baidu_analytics_service.update_config(db, config_id, updates)

    return ok(
        data={
            'id': config.id,
            'site_token': config.site_token,
        },
        msg="Baidu Analytics configuration updated successfully"
    )


@router.delete("/config/{config_id}", summary="停用百度统计配置")
@_catch
async def deactivate_baidu_config(
        config_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    停用百度统计配置
    
    Args:
        config_id: 配置 ID
        
    Returns:
        操作结果
    """
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    await baidu_analytics_service.deactivate_config(db, config_id)

    return ok(
        msg="Baidu Analytics configuration deactivated successfully"
    )


@router.get("/tracking-code", summary="获取百度统计追踪代码")
@_catch
async def get_tracking_code(
        site_id: Optional[int] = Query(None, description="站点 ID（为空则获取全局配置）"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取百度统计追踪代码（用于前端嵌入）
    
    Args:
        site_id: 站点 ID（可选）
        
    Returns:
        HTML/JavaScript 追踪代码
    """
    config = await baidu_analytics_service.get_config(db, site_id)

    if not config or not config.is_active:
        return ok(
            data={'tracking_code': ''},
            msg="Baidu Analytics is not configured or inactive"
        )

    tracking_code = baidu_analytics_service.generate_tracking_code(config)

    return ok(
        data={
            'tracking_code': tracking_code,
            'config': {
                'site_token': config.site_token,
                'enable_tracking': config.enable_tracking,
            }
        }
    )


@router.get("/configs", summary="获取所有百度统计配置")
@_catch
async def get_all_configs(
        include_inactive: bool = Query(False, description="是否包含非活动配置"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取所有百度统计配置（管理员用）
    
    Args:
        include_inactive: 是否包含非活动配置
        
    Returns:
        配置列表
    """
    # 检查权限
    has_permission = await check_admin_permission(db, current_user.id)
    if not has_permission:
        return fail("Insufficient permissions")

    configs = await baidu_analytics_service.get_all_configs(db, include_inactive)

    configs_list = []
    for config in configs:
        configs_list.append({
            'id': config.id,
            'site_id': config.site_id,
            'site_token': config.site_token,
            'enable_tracking': config.enable_tracking,
            'enable_data_sync': config.enable_data_sync,
            'is_active': config.is_active,
            'created_at': config.created_at.isoformat() if config.created_at else None,
        })

    return ok(
        data={
            'configs': configs_list,
            'total': len(configs_list)
        }
    )
