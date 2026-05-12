"""
对象缓存管理 API

提供对象缓存的管理、监控和清除功能
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Body

from shared.services.object_cache import object_cache_service
from api.v1.core.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.get("/stats", summary="获取对象缓存统计", description="获取对象缓存的统计信息")
async def get_object_cache_stats(
        current_user=Depends(jwt_required),
):
    """获取对象缓存统计"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    stats = await object_cache_service.get_stats()

    return ApiResponse(
        success=True,
        data=stats
    )


@router.post("/invalidate-tag", summary="按标签清除缓存", description="使指定标签的所有缓存失效")
async def invalidate_by_tag(
        tag: str = Body(..., description="缓存标签"),
        current_user=Depends(jwt_required),
):
    """按标签清除缓存"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        count = await object_cache_service.invalidate_by_tag(tag)

        return ApiResponse(
            success=True,
            message=f"Invalidated {count} cached objects with tag: {tag}",
            data={"count": count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invalidate by tag: {str(e)}")


@router.post("/invalidate-tags", summary="批量按标签清除", description="使多个标签的缓存失效")
async def invalidate_by_tags(
        tags: List[str] = Body(..., description="缓存标签列表"),
        current_user=Depends(jwt_required),
):
    """批量按标签清除缓存"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        count = await object_cache_service.invalidate_by_tags(tags)

        return ApiResponse(
            success=True,
            message=f"Invalidated {count} cached objects",
            data={"count": count, "tags": tags}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invalidate by tags: {str(e)}")


@router.post("/config", summary="更新缓存配置", description="更新对象缓存配置")
async def update_cache_config(
        ttl: int = Body(None, ge=1, le=86400, description="默认TTL(秒)"),
        current_user=Depends(jwt_required),
):
    """更新对象缓存配置"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    if ttl is not None:
        object_cache_service.default_ttl = ttl

    return ApiResponse(
        success=True,
        message="Cache configuration updated",
        data={
            "default_ttl": object_cache_service.default_ttl,
        }
    )


@router.get("/examples", summary="使用示例", description="获取对象缓存使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "cache_single_object": {
            "description": "缓存单个对象",
            "code": '''
from shared.services.object_cache import object_cache_service

# 缓存文章对象
await object_cache_service.set_object(
    model_name="Article",
    object_id=article_id,
    data=article_data,
    ttl=600,
    tags=["article", f"article:{article_id}"]
)

# 获取缓存
cached = await object_cache_service.get_object("Article", article_id)
            '''.strip()
        },
        "cache_query_result": {
            "description": "缓存查询结果",
            "code": '''
# 缓存文章列表查询
await object_cache_service.set_query_result(
    query_type="article_list",
    params={"category_id": 1, "page": 1},
    data=articles_list,
    ttl=300,
    tags=["article_list", "category:1"]
)

# 获取缓存
cached = await object_cache_service.get_query_result(
    "article_list",
    {"category_id": 1, "page": 1}
)
            '''.strip()
        },
        "invalidate_on_update": {
            "description": "更新时清除缓存",
            "code": '''
async def update_article(article_id: int, data: dict):
    # 更新数据库
    await db.update(...)
    
    # 清除相关缓存
    await object_cache_service.invalidate_by_tag(f"article:{article_id}")
    await object_cache_service.invalidate_by_tag("article_list")
            '''.strip()
        },
        "use_decorator": {
            "description": "使用装饰器自动缓存",
            "code": '''
from shared.services.object_cache import object_cache_service

@object_cache_service.cache_object(
    model_name="Article",
    ttl=600,
    tags=["article"]
)
async def get_article_detail(article_id: int):
    # 这个函数的结果会被自动缓存
    article = await db.get(Article, article_id)
    return serialize_article(article)
            '''.strip()
        },
        "common_tags": {
            "description": "常用缓存标签",
            "tags": [
                "article - 所有文章相关缓存",
                "article:{id} - 特定文章缓存",
                "article_list - 文章列表缓存",
                "category:{id} - 分类相关缓存",
                "user:{id} - 用户相关缓存",
                "settings - 系统设置缓存",
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
