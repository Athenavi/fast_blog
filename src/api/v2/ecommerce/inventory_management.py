"""
库存管理 API

提供库存检查、库存调整、低库存警告、库存报告等功能
"""
from typing import Optional
from functools import wraps

from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from shared.services.ecommerce.inventory_service import create_inventory_service
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required, admin_required as admin_required_api
from src.utils.database.main import get_async_session as get_async_db

router = APIRouter(tags=["inventory"])


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


@router.get("/check/{product_id}")
@_catch
async def check_product_inventory(
        product_id: int,
        quantity: int = Query(1, ge=1, description="需要检查的数量"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    检查产品库存
    
    Args:
        product_id: 产品ID
        quantity: 需要检查的数量
        
    Returns:
        库存检查结果
    """
    service = create_inventory_service(db)
    result = await service.check_inventory(product_id, quantity)

    return ok(data=result)


@router.post("/deduct")
@_catch
async def deduct_product_inventory(
        product_id: int = Body(..., embed=True, description="产品ID"),
        quantity: int = Body(..., embed=True, ge=1, description="扣减数量"),
        order_id: Optional[int] = Body(None, embed=True, description="关联订单ID"),
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    扣减库存（用于订单支付成功后）
    
    Args:
        product_id: 产品ID
        quantity: 扣减数量
        order_id: 关联订单ID（可选）
        
    Returns:
        扣减结果
    """
    service = create_inventory_service(db)
    result = await service.deduct_inventory(
        product_id=product_id,
        quantity=quantity,
        order_id=order_id,
        user_id=current_user.id
    )

    if not result['success']:
        return fail(result['message'])

    return ok(data=result)


@router.post("/restore")
@_catch
async def restore_product_inventory(
        product_id: int = Body(..., embed=True, description="产品ID"),
        quantity: int = Body(..., embed=True, ge=1, description="恢复数量"),
        order_id: Optional[int] = Body(None, embed=True, description="关联订单ID"),
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    恢复库存（用于订单取消或退款时）
    
    Args:
        product_id: 产品ID
        quantity: 恢复数量
        order_id: 关联订单ID（可选）
        
    Returns:
        恢复结果
    """
    service = create_inventory_service(db)
    result = await service.restore_inventory(
        product_id=product_id,
        quantity=quantity,
        order_id=order_id,
        user_id=current_user.id
    )

    if not result['success']:
        return fail(result['message'])

    return ok(data=result)


@router.post("/adjust")
@_catch
async def adjust_product_inventory(
        product_id: int = Body(..., embed=True, description="产品ID"),
        new_quantity: int = Body(..., embed=True, ge=0, description="新的库存数量"),
        reason: str = Body('', description="调整原因"),
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    手动调整库存（仅管理员）
    
    Args:
        product_id: 产品ID
        new_quantity: 新的库存数量
        reason: 调整原因
        
    Returns:
        调整结果
    """
    service = create_inventory_service(db)
    result = await service.adjust_inventory(
        product_id=product_id,
        new_quantity=new_quantity,
        reason=reason,
        user_id=current_user.id
    )

    if not result['success']:
        return fail(result['message'])

    return ok(data=result)


@router.get("/low-stock")
@_catch
async def get_low_stock_products(
        threshold: int = Query(10, ge=0, description="低库存阈值"),
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取低库存产品列表
    
    Args:
        threshold: 低库存阈值（默认10）
        
    Returns:
        低库存产品列表
    """
    service = create_inventory_service(db)
    low_stock_products = await service.get_low_stock_products(threshold)

    return ok(data={
        'products': low_stock_products,
        'count': len(low_stock_products),
        'threshold': threshold
    })


@router.get("/report")
@_catch
async def get_inventory_report(
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取库存报告
    
    Returns:
        库存报告数据
    """
    service = create_inventory_service(db)
    report = await service.get_inventory_report()

    return ok(data=report)
