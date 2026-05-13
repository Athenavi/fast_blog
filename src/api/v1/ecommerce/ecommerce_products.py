"""
电子商务产品管理 API

注意：此模块已废弃，功能已合并到 ecommerce.py 中。
保留此文件仅为向后兼容，所有路由已禁用。

提供产品的增删改查、分类管理等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from src.api.v1.core.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

# 此路由器已禁用，功能已迁移到 ecommerce.py
router = APIRouter(tags=["ecommerce-products"], include_in_schema=False)


# ============================================================================
# 以下路由已废弃，请使用 /api/v2/shop/products 下的端点
# ============================================================================

# @router.get("/")
# async def list_products(...):
#     """已废弃 - 请使用 ecommerce.py 中的实现"""
#     pass


# ============================================================================
# 产品分类管理
# ============================================================================

@router.get("/categories")
async def list_categories(
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取产品分类列表
    """
    try:
        return ApiResponse(
            success=True,
            data={"categories": []},
            message="分类列表获取成功（待实现）"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categories")
async def create_category(
        category_data: dict = Body(...),
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建产品分类
    
    Body参数:
        name: 分类名称
        slug: 分类标识
        description: 分类描述
        parent_id: 父分类ID（支持层级分类）
    """
    try:
        return ApiResponse(
            success=True,
            data={"category_id": 1},
            message="分类创建成功（待实现）"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
