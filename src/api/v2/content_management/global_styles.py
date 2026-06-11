"""
全局样式（Global Styles）API 端点
提供全局样式配置的查询和管理功能
"""
import json
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.theme import GlobalStyle, GlobalStyleConfig
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["global-styles"])


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


@router.get("")
@router.get("/list")
@_catch
async def list_global_styles(
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db),
):
    """
    获取全局样式列表

    Returns:
        全局样式配置列表
    """
    # 查询 GlobalStyleConfig 表
    query = select(GlobalStyleConfig).order_by(desc(GlobalStyleConfig.is_active), GlobalStyleConfig.id)
    result = await db.execute(query)
    configs = result.scalars().all()

    styles = []
    for config in configs:
        style_data = {
            "id": config.id,
            "name": config.name,
            "slug": config.slug,
            "is_active": config.is_active,
            "theme_type": config.theme_type,
            "color_scheme": _safe_json_parse(config.color_scheme, {}),
            "typography": _safe_json_parse(config.typography, {}),
            "spacing": _safe_json_parse(config.spacing, {}),
            "border_radius": _safe_json_parse(config.border_radius, {}),
            "shadows": _safe_json_parse(config.shadows, {}),
            "breakpoints": _safe_json_parse(config.breakpoints, {}),
            "css_variables": _safe_json_parse(config.css_variables, {}),
            "preview_image": config.preview_image,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }
        styles.append(style_data)

    # 如果 GlobalStyleConfig 为空，尝试从 GlobalStyle 表获取
    if not styles:
        gs_query = select(GlobalStyle).order_by(desc(GlobalStyle.is_active), GlobalStyle.id)
        gs_result = await db.execute(gs_query)
        gs_configs = gs_result.scalars().all()

        for gs in gs_configs:
            style_data = {
                "id": gs.id,
                "name": gs.theme_name or f"Style #{gs.id}",
                "slug": gs.theme_name or f"style-{gs.id}",
                "is_active": gs.is_active,
                "theme_type": "legacy",
                "variables": _safe_json_parse(gs.variables_json, {}),
                "created_at": gs.created_at.isoformat() if gs.created_at else None,
            }
            styles.append(style_data)

    return ok(data=styles)


@router.get("/{style_id}")
@_catch
async def get_global_style(
    style_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db),
):
    """获取单个全局样式详情"""
    result = await db.execute(
        select(GlobalStyleConfig).where(GlobalStyleConfig.id == style_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        return fail("全局样式不存在")

    return ok(data=config.to_dict())


@router.post("")
@_catch
async def create_global_style(
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db),
    name: str = Body(...),
    slug: Optional[str] = Body(None),
    theme_type: str = Body("custom"),
    color_scheme: str = Body("{}"),
    typography: str = Body("{}"),
    spacing: str = Body("{}"),
    border_radius: str = Body("{}"),
    shadows: Optional[str] = Body(None),
    breakpoints: Optional[str] = Body(None),
    css_variables: Optional[str] = Body(None),
):
    """创建全局样式配置"""
    if not slug:
        slug = name.lower().replace(" ", "-")

    new_config = GlobalStyleConfig(
        name=name,
        slug=slug,
        theme_type=theme_type,
        color_scheme=color_scheme,
        typography=typography,
        spacing=spacing,
        border_radius=border_radius,
        shadows=shadows,
        breakpoints=breakpoints,
        css_variables=css_variables,
        created_by=current_user.id,
    )

    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)

    return ok(msg="全局样式创建成功", data=new_config.to_dict())


@router.post("/{style_id}/activate")
@_catch
async def activate_global_style(
    style_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db),
):
    """激活指定全局样式"""
    result = await db.execute(
        select(GlobalStyleConfig).where(GlobalStyleConfig.id == style_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        return fail("全局样式不存在")

    # 取消所有已激活的样式
    from sqlalchemy import update
    await db.execute(
        update(GlobalStyleConfig).values(is_active=False)
    )

    # 激活目标样式
    config.is_active = True
    await db.commit()

    return ok(msg=f"已激活样式: {config.name}")


@router.delete("/{style_id}")
@_catch
async def delete_global_style(
    style_id: int,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db),
):
    """删除全局样式"""
    result = await db.execute(
        select(GlobalStyleConfig).where(GlobalStyleConfig.id == style_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        return fail("全局样式不存在")

    if config.is_active:
        return fail("不能删除当前激活的样式")

    await db.delete(config)
    await db.commit()

    return ok(msg="全局样式已删除")


def _safe_json_parse(json_str: Optional[str], default=None):
    """安全解析 JSON 字符串"""
    if not json_str:
        return default if default is not None else {}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}
