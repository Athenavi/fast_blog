"""
自定义内容类型API
提供CPT的CRUD操作
"""

from datetime import datetime
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.content import CustomPostType
from shared.models.user import User
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["custom-post-types"])


class CustomPostTypeCreate(BaseModel):
    """创建CPT请求"""
    name: str
    slug: str
    description: Optional[str] = None
    supports: Optional[str] = None
    has_archive: bool = False
    menu_icon: Optional[str] = None
    menu_position: int = 5


class CustomPostTypeUpdate(BaseModel):
    """更新CPT请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    supports: Optional[str] = None
    has_archive: Optional[bool] = None
    menu_icon: Optional[str] = None
    menu_position: Optional[int] = None
    is_active: Optional[bool] = None


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
@_catch
async def list_custom_post_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """获取自定义内容类型列表"""
    from sqlalchemy import func

    # 获取总数
    count_result = await db.execute(select(func.count()).select_from(CustomPostType))
    total = count_result.scalar()

    # 获取列表
    result = await db.execute(
        select(CustomPostType).offset(skip).limit(limit)
    )
    items = result.scalars().all()

    return ok(data={
        'items': [item.to_dict() for item in items],
        'total': total,
        'skip': skip,
        'limit': limit
    })


@router.post("")
@_catch
async def create_custom_post_type(
    data: CustomPostTypeCreate,
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """创建自定义内容类型"""
    # 检查 slug 唯一性
    existing = await db.scalar(select(CustomPostType).where(CustomPostType.slug == data.slug))
    if existing:
        return fail(f"Slug '{data.slug}' 已存在")
    cpt = CustomPostType(
        name=data.name,
        slug=data.slug,
        description=data.description,
        supports=data.supports,
        has_archive=data.has_archive,
        menu_icon=data.menu_icon,
        menu_position=data.menu_position,
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    db.add(cpt)
    await db.commit()
    await db.refresh(cpt)

    return ok(msg="创建成功", data=cpt.to_dict())


@router.get("/{cpt_id}")
@_catch
async def get_custom_post_type(cpt_id: int,
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """获取自定义内容类型详情"""
    result = await db.execute(
        select(CustomPostType).where(CustomPostType.id == cpt_id)
    )
    cpt = result.scalar_one_or_none()

    if not cpt:
        return fail("内容类型不存在")

    return ok(data=cpt.to_dict())


@router.put("/{cpt_id}")
@_catch
async def update_custom_post_type(
    cpt_id: int,
    data: CustomPostTypeUpdate,
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """更新自定义内容类型"""
    result = await db.execute(
        select(CustomPostType).where(CustomPostType.id == cpt_id)
    )
    cpt = result.scalar_one_or_none()

    if not cpt:
        return fail("内容类型不存在")

    if data.name is not None:
        cpt.name = data.name
    if data.description is not None:
        cpt.description = data.description
    if data.supports is not None:
        cpt.supports = data.supports
    if data.has_archive is not None:
        cpt.has_archive = data.has_archive
    if data.menu_icon is not None:
        cpt.menu_icon = data.menu_icon
    if data.menu_position is not None:
        cpt.menu_position = data.menu_position
    if data.is_active is not None:
        cpt.is_active = data.is_active

    cpt.updated_at = datetime.now()

    await db.commit()
    await db.refresh(cpt)

    return ok(msg="更新成功", data=cpt.to_dict())


@router.delete("/{cpt_id}")
@_catch
async def delete_custom_post_type(cpt_id: int,
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """删除自定义内容类型"""
    result = await db.execute(
        select(CustomPostType).where(CustomPostType.id == cpt_id)
    )
    cpt = result.scalar_one_or_none()

    if not cpt:
        return fail("内容类型不存在")

    # 先删除关联的内容记录，避免孤儿数据
    from sqlalchemy import delete as sa_delete
    from shared.models.content import CustomPostContent
    await db.execute(
        sa_delete(CustomPostContent).where(CustomPostContent.post_type_id == cpt_id)
    )

    await db.delete(cpt)
    await db.commit()

    return ok(msg="删除成功")
