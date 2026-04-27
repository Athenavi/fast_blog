"""
Redis 缓存管理 API
提供缓存查看、清除和统计功能
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.user.models import User
from src.auth import jwt_required_dependency as jwt_required
from src.services.redis_service import redis_service

router = APIRouter(tags=["cache"])


@router.get("/cache/stats")
async def get_cache_stats(
        current_user: User = Depends(jwt_required),
):
    """获取缓存统计信息"""
    stats = await redis_service.get_stats()
    return {"success": True, "data": stats}


@router.get("/cache/keys")
async def list_cache_keys(
        pattern: str = Query(default="*", description="键名模式（支持通配符）"),
        limit: int = Query(default=100, ge=1, le=1000, description="返回数量限制"),
        current_user: User = Depends(jwt_required),
):
    """列出缓存键"""
    try:
        keys = []
        async for key in redis_service.redis.scan_iter(match=pattern, count=limit):
            keys.append(key)
            if len(keys) >= limit:
                break

        return {
            "success": True,
            "data": {
                "keys": keys,
                "total": len(keys),
                "pattern": pattern,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存键失败: {str(e)}")


@router.get("/cache/{key:path}")
async def get_cache_value(
        key: str,
        current_user: User = Depends(jwt_required),
):
    """获取缓存值"""
    value = await redis_service.get(key)

    if value is None:
        raise HTTPException(status_code=404, detail="缓存键不存在")

    return {
        "success": True,
        "data": {
            "key": key,
            "value": value,
        }
    }


@router.delete("/cache/{key:path}")
async def delete_cache_key(
        key: str,
        current_user: User = Depends(jwt_required),
):
    """删除缓存键"""
    deleted = await redis_service.delete(key)

    return {
        "success": True,
        "data": {
            "deleted": deleted,
            "key": key,
        },
        "message": f"成功删除 {deleted} 个缓存键"
    }


@router.post("/cache/clear")
async def clear_cache(
        pattern: Optional[str] = Query(default=None, description="清除匹配模式的键（不填则清空全部）"),
        current_user: User = Depends(jwt_required),
):
    """清除缓存"""
    try:
        if pattern:
            # 清除匹配模式的键
            deleted_count = 0
            async for key in redis_service.redis.scan_iter(match=pattern):
                await redis_service.delete(key)
                deleted_count += 1

            return {
                "success": True,
                "data": {"deleted": deleted_count, "pattern": pattern},
                "message": f"成功清除 {deleted_count} 个缓存键"
            }
        else:
            # 清空整个数据库（危险操作）
            success = await redis_service.flushdb()

            if not success:
                raise HTTPException(status_code=500, detail="清空缓存失败")

            return {
                "success": True,
                "message": "缓存已清空",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")


@router.post("/cache/warmup")
async def warmup_cache(
        cache_types: Optional[List[str]] = Query(
            default=None,
            description="要预热的缓存类型：articles, categories, tags, config"
        ),
        current_user: User = Depends(jwt_required),
):
    """预热缓存"""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.extensions import get_async_db_session as get_async_db
    from shared.models.article import Article
    from apps.category.models import Category

    db: AsyncSession = next(get_async_db())

    warmed_up = {}
    
    try:
        # 如果没有指定类型，预热所有类型
        types_to_warmup = cache_types or ["articles", "categories", "tags"]

        for cache_type in types_to_warmup:
            if cache_type == "articles":
                # 预热热门文章
                stmt = (
                    select(Article)
                    .where(Article.status == 'published')
                    .order_by(Article.views.desc())
                    .limit(20)
                )
                result = await db.execute(stmt)
                articles = result.scalars().all()

                # 缓存每篇文章
                for article in articles:
                    cache_key = f"article:{article.id}"
                    await redis_service.set(
                        cache_key,
                        {
                            "id": article.id,
                            "title": article.title,
                            "views": article.views,
                        },
                        expire=3600,  # 1小时
                    )

                warmed_up[cache_type] = len(articles)

            elif cache_type == "categories":
                # 预热分类列表
                stmt = select(Category).order_by(Category.name)
                result = await db.execute(stmt)
                categories = result.scalars().all()

                cache_key = "categories:all"
                await redis_service.set(
                    cache_key,
                    [{"id": c.id, "name": c.name, "slug": c.slug} for c in categories],
                    expire=7200,  # 2小时
                )

                warmed_up[cache_type] = len(categories)

        return {
            "success": True,
            "data": warmed_up,
            "message": f"成功预热 {len(warmed_up)} 个缓存类型"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"缓存预热失败: {str(e)}")
    finally:
        await db.close()
