"""
块模式（Block Patterns）API 端点
"""

from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query

from shared.services.content_management.block_pattern_library import block_pattern_library
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required

router = APIRouter(tags=["block-patterns"])


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
async def list_block_patterns(
    category: str = Query(None, description="分类过滤"),
    current_user=Depends(jwt_required)
):
    """
    获取所有块模式列表

    Args:
        category: 可选的分类过滤

    Returns:
        块模式列表
    """
    patterns = block_pattern_library.get_all_patterns(category=category)

    return ok(data={
        "patterns": patterns,
        "total": len(patterns),
        "categories": block_pattern_library.get_categories()
    })


@router.get("/categories")
@_catch
async def get_pattern_categories(
    current_user=Depends(jwt_required)
):
    """
    获取所有块模式分类

    Returns:
        分类列表
    """
    categories = block_pattern_library.get_categories()

    return ok(data={"categories": categories})


@router.get("/search")
@_catch
async def search_block_patterns(
    q: str = Query(..., description="搜索关键词"),
    current_user=Depends(jwt_required)
):
    """
    搜索块模式

    Args:
        q: 搜索关键词

    Returns:
        匹配的块模式列表
    """
    if not q or len(q.strip()) == 0:
        return fail("请提供搜索关键词")

    patterns = block_pattern_library.search_patterns(q)

    return ok(data={
        "patterns": patterns,
        "total": len(patterns),
        "query": q
    })


@router.get("/{pattern_slug}")
@_catch
async def get_block_pattern(
    pattern_slug: str,
    current_user=Depends(jwt_required)
):
    """
    获取单个块模式详情

    Args:
        pattern_slug: 模式标识

    Returns:
        块模式详情
    """
    pattern = block_pattern_library.get_pattern_by_slug(pattern_slug)

    if not pattern:
        return fail(f"块模式不存在: {pattern_slug}")

    return ok(data={"pattern": pattern})
