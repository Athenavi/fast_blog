"""
搜索与媒体管理扩展 API

提供搜索索引(SearchIndex)和媒体优化(MediaOptimization)的 CRUD 管理接口
"""
import json
from datetime import datetime
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import SearchIndex, MediaOptimization
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["search-media-management"])


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


def _is_admin(user) -> bool:
    return getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False)


# ==================== 搜索索引管理 ====================


@router.get("/search-index")
@_catch
async def list_search_index(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    indexed: Optional[bool] = Query(None, description="是否已索引"),
    article_id: Optional[int] = Query(None, description="文章ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """
    获取搜索索引列表

    支持分页、按索引状态和文章ID筛选
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(SearchIndex)

    if indexed is not None:
        query = query.where(SearchIndex.indexed == indexed)

    if article_id:
        query = query.where(SearchIndex.article_id == article_id)

    query = query.order_by(SearchIndex.updated_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    indexes = result.scalars().all()

    return ok(data={
        "search_indexes": [idx.to_dict() for idx in indexes],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    })


@router.get("/search-index/{index_id}")
@_catch
async def get_search_index(
    index_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """获取搜索索引详情"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(SearchIndex).where(SearchIndex.id == index_id)
    result = await db.execute(query)
    index = result.scalar_one_or_none()

    if not index:
        return fail("搜索索引记录不存在")

    return ok(data=index.to_dict())


@router.post("/search-index")
@_catch
async def create_search_index(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """创建搜索索引记录"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    data = await request.json()

    article_id = data.get("article_id")
    if not article_id:
        return fail("article_id 为必填字段")

    existing = await db.execute(
        select(SearchIndex).where(SearchIndex.article_id == article_id)
    )
    if existing.scalar_one_or_none():
        return fail(f"文章 ID={article_id} 的索引记录已存在")

    now = datetime.utcnow()
    index = SearchIndex(
        article_id=article_id,
        indexed=data.get("indexed", False),
        last_indexed_at=data.get("last_indexed_at"),
        index_hash=data.get("index_hash"),
        created_at=now,
        updated_at=now,
    )

    db.add(index)
    try:
        await db.commit()
        await db.refresh(index)
    except Exception:
        await db.rollback()
        raise

    return ok(data=index.to_dict(), msg="搜索索引记录创建成功")


@router.put("/search-index/{index_id}")
@_catch
async def update_search_index(
    index_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """更新搜索索引记录"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(SearchIndex).where(SearchIndex.id == index_id)
    result = await db.execute(query)
    index = result.scalar_one_or_none()

    if not index:
        return fail("搜索索引记录不存在")

    data = await request.json()

    if "indexed" in data:
        index.indexed = data["indexed"]
    if "index_hash" in data:
        index.index_hash = data["index_hash"]
    if "last_indexed_at" in data:
        lia = data["last_indexed_at"]
        index.last_indexed_at = datetime.fromisoformat(lia.replace("Z", "+00:00")) if isinstance(lia, str) else lia

    if data.get("indexed") is True and index.last_indexed_at is None:
        index.last_indexed_at = datetime.utcnow()

    index.updated_at = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(index)
    except Exception:
        await db.rollback()
        raise

    return ok(data=index.to_dict(), msg="搜索索引记录更新成功")


@router.delete("/search-index/{index_id}")
@_catch
async def delete_search_index(
    index_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """删除搜索索引记录"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(SearchIndex).where(SearchIndex.id == index_id)
    result = await db.execute(query)
    index = result.scalar_one_or_none()

    if not index:
        return fail("搜索索引记录不存在")

    await db.delete(index)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="搜索索引记录删除成功")


@router.post("/search-index/batch-reindex")
@_catch
async def batch_reindex(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """
    批量标记需要重新索引

    将指定文章或所有文章的索引状态重置为待索引
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    data = await request.json()
    article_ids = data.get("article_ids")

    if article_ids and isinstance(article_ids, list):
        count = 0
        for aid in article_ids:
            query = select(SearchIndex).where(SearchIndex.article_id == aid)
            result = await db.execute(query)
            index = result.scalar_one_or_none()
            if index:
                index.indexed = False
                index.index_hash = None
                index.updated_at = datetime.utcnow()
                count += 1
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return ok(data={"reset_count": count}, msg=f"已重置 {count} 条索引记录")
    else:
        from sqlalchemy import update
        try:
            await db.execute(
                update(SearchIndex)
                .values(indexed=False, index_hash=None, updated_at=datetime.utcnow())
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        total = await db.execute(select(func.count()).select_from(SearchIndex))
        total_count = total.scalar()
        return ok(
            data={"reset_count": total_count},
            msg=f"已重置全部 {total_count} 条索引记录",
        )


# ==================== 媒体优化管理 ====================


@router.get("/media-optimizations")
@_catch
async def list_media_optimizations(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    media_id: Optional[int] = Query(None, description="媒体ID"),
    optimization_status: Optional[str] = Query(None, description="优化状态"),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """
    获取媒体优化配置列表

    支持分页、按媒体ID和优化状态筛选
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(MediaOptimization)

    if media_id:
        query = query.where(MediaOptimization.media_id == media_id)

    if optimization_status:
        query = query.where(MediaOptimization.optimization_status == optimization_status)

    query = query.order_by(MediaOptimization.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    optimizations = result.scalars().all()

    return ok(data={
        "media_optimizations": [o.to_dict() for o in optimizations],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    })


@router.get("/media-optimizations/{opt_id}")
@_catch
async def get_media_optimization(
    opt_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """获取媒体优化配置详情"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(MediaOptimization).where(MediaOptimization.id == opt_id)
    result = await db.execute(query)
    opt = result.scalar_one_or_none()

    if not opt:
        return fail("媒体优化配置不存在")

    return ok(data=opt.to_dict())


@router.post("/media-optimizations")
@_catch
async def create_media_optimization(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """创建媒体优化配置"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    data = await request.json()

    media_id = data.get("media_id")
    if not media_id:
        return fail("media_id 为必填字段")

    existing = await db.execute(
        select(MediaOptimization).where(MediaOptimization.media_id == media_id)
    )
    if existing.scalar_one_or_none():
        return fail(f"媒体 ID={media_id} 的优化配置已存在")

    now = datetime.utcnow()
    opt = MediaOptimization(
        media_id=media_id,
        webp_url=data.get("webp_url"),
        sizes_json=json.dumps(data["sizes_json"], ensure_ascii=False)
        if "sizes_json" in data and isinstance(data["sizes_json"], dict)
        else data.get("sizes_json"),
        cdn_url=data.get("cdn_url"),
        optimization_status=data.get("optimization_status", "pending"),
        created_at=now,
        updated_at=now,
    )

    db.add(opt)
    try:
        await db.commit()
        await db.refresh(opt)
    except Exception:
        await db.rollback()
        raise

    return ok(data=opt.to_dict(), msg="媒体优化配置创建成功")


@router.put("/media-optimizations/{opt_id}")
@_catch
async def update_media_optimization(
    opt_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """更新媒体优化配置"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(MediaOptimization).where(MediaOptimization.id == opt_id)
    result = await db.execute(query)
    opt = result.scalar_one_or_none()

    if not opt:
        return fail("媒体优化配置不存在")

    data = await request.json()

    if "webp_url" in data:
        opt.webp_url = data["webp_url"]
    if "cdn_url" in data:
        opt.cdn_url = data["cdn_url"]
    if "optimization_status" in data:
        opt.optimization_status = data["optimization_status"]
    if "sizes_json" in data:
        sj = data["sizes_json"]
        opt.sizes_json = json.dumps(sj, ensure_ascii=False) if isinstance(sj, dict) else sj

    opt.updated_at = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(opt)
    except Exception:
        await db.rollback()
        raise

    return ok(data=opt.to_dict(), msg="媒体优化配置更新成功")


@router.delete("/media-optimizations/{opt_id}")
@_catch
async def delete_media_optimization(
    opt_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """删除媒体优化配置"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(MediaOptimization).where(MediaOptimization.id == opt_id)
    result = await db.execute(query)
    opt = result.scalar_one_or_none()

    if not opt:
        return fail("媒体优化配置不存在")

    await db.delete(opt)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="媒体优化配置删除成功")
