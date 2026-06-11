"""
自定义块模式 API 端点
"""

from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.content_management.custom_block_pattern import custom_block_pattern_service
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required

router = APIRouter(tags=["custom-patterns"])


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


@router.post("")
@_catch
async def create_custom_pattern(
    title: str = Body(..., description="模式标题"),
    description: str = Body(..., description="描述"),
    blocks: list = Body(..., description="区块数据"),
    category: str = Body("custom", description="分类"),
    tags: list = Body(None, description="标签"),
    current_user=Depends(jwt_required)
):
    """创建自定义块模式"""
    # 从 JWT token 获取 user_id
    user_id = current_user.id if hasattr(current_user, 'id') else None

    if not user_id:
        return fail("未授权，请先登录")

    result = await custom_block_pattern_service.save_pattern(
        user_id=user_id,
        title=title,
        description=description,
        blocks=blocks,
        category=category,
        tags=tags
    )

    if result["success"]:
        return ok(msg=result["message"], data={"pattern": result["pattern"]})
    else:
        return fail(result["error"])


@router.get("")
@_catch
async def list_user_patterns(
    category: str = Query(None, description="分类过滤"),
    current_user=Depends(jwt_required)
):
    """获取用户的自定义块模式列表"""
    user_id = getattr(current_user, 'id', 1)

    patterns = await custom_block_pattern_service.get_user_patterns(user_id, category)

    return ok(data={
        "patterns": patterns,
        "total": len(patterns),
        "categories": await custom_block_pattern_service.get_categories(user_id)
    })


@router.get("/{pattern_id}")
@_catch
async def get_pattern_detail(
    pattern_id: int,
    current_user=Depends(jwt_required)
):
    """获取块模式详情"""
    user_id = getattr(current_user, 'id', 1)

    pattern = await custom_block_pattern_service.get_pattern_by_id(user_id, pattern_id)

    if not pattern:
        return fail("块模式不存在")

    return ok(data={"pattern": pattern})


@router.put("/{pattern_id}")
@_catch
async def update_pattern(
    pattern_id: int,
    title: str = Body(None, description="模式标题"),
    description: str = Body(None, description="描述"),
    blocks: list = Body(None, description="区块数据"),
    category: str = Body(None, description="分类"),
    tags: list = Body(None, description="标签"),
    current_user=Depends(jwt_required)
):
    """更新块模式"""
    user_id = getattr(current_user, 'id', 1)

    result = await custom_block_pattern_service.update_pattern(
        user_id=user_id,
        pattern_id=pattern_id,
        title=title,
        description=description,
        blocks=blocks,
        category=category,
        tags=tags
    )

    if result["success"]:
        return ok(msg=result["message"], data={"pattern": result["pattern"]})
    else:
        return fail(result["error"])


@router.delete("/{pattern_id}")
@_catch
async def delete_pattern(
    pattern_id: int,
    current_user=Depends(jwt_required)
):
    """删除块模式"""
    user_id = getattr(current_user, 'id', 1)

    result = await custom_block_pattern_service.delete_pattern(user_id, pattern_id)

    if result["success"]:
        return ok(msg=result["message"])
    else:
        return fail(result["error"])
