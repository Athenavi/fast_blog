"""
会员订阅 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.core.membership import create_membership_service
from src.utils.database.main import get_async_session

router = APIRouter(tags=["membership"])


class CreateSubscriptionRequest(BaseModel):
    """创建订阅请求"""
    plan_id: int
    payment_amount: float
    transaction_id: Optional[str] = None


@router.get("/status")
async def get_vip_status(
        user_id: int = Query(..., description="用户ID"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取用户 VIP 状态
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        VIP 状态信息
    """
    try:
        service = create_membership_service(db)
        status = await service.get_user_vip_status(user_id)

        return {
            'success': True,
            'data': status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-access")
async def check_content_access(
        user_id: int = Query(..., description="用户ID"),
        article_id: int = Query(..., description="文章ID"),
        required_level: int = Query(0, ge=0, le=10, description="所需VIP等级"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    检查内容访问权限
    
    Args:
        user_id: 用户ID
        article_id: 文章ID
        required_level: 所需VIP等级
        db: 数据库会话
        
    Returns:
        访问权限结果
    """
    try:
        service = create_membership_service(db)
        result = await service.check_content_access(user_id, article_id, required_level)

        return {
            'success': True,
            'data': result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscribe")
async def create_subscription(
        request: CreateSubscriptionRequest,
        user_id: int = Query(..., description="用户ID"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    创建订阅
    
    Args:
        request: 订阅请求
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        订阅结果
    """
    try:
        service = create_membership_service(db)
        result = await service.create_subscription(
            user_id=user_id,
            plan_id=request.plan_id,
            payment_amount=request.payment_amount,
            transaction_id=request.transaction_id
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{subscription_id}")
async def cancel_subscription(
        subscription_id: int,
        user_id: int = Query(..., description="用户ID"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    取消订阅
    
    Args:
        subscription_id: 订阅ID
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = create_membership_service(db)
        result = await service.cancel_subscription(subscription_id, user_id)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans")
async def get_available_plans(
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取可用套餐列表
    
    Args:
        db: 数据库会话
        
    Returns:
        套餐列表
    """
    try:
        service = create_membership_service(db)
        plans = await service.get_available_plans()

        return {
            'success': True,
            'data': plans,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions")
async def get_user_subscriptions(
        user_id: int = Query(..., description="用户ID"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取用户订阅历史
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        订阅列表
    """
    try:
        service = create_membership_service(db)
        subscriptions = await service.get_user_subscriptions(user_id)

        return {
            'success': True,
            'data': subscriptions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
