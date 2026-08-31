"""
会员订阅 API - 统一会员/VIP功能模块
整合了原有的 vip.py 和 membership.py 功能
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from shared.services.core.membership import create_membership_service
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["membership"])


class CreateSubscriptionRequest(BaseModel):
    """创建订阅请求"""
    plan_id: int
    payment_amount: float
    transaction_id: Optional[str] = None


@router.get("/status")
@_catch
async def get_vip_status(
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取当前用户的 VIP 状态"""
    service = create_membership_service(db)
    status = await service.get_user_vip_status(current_user.id)
    return ok(data=status)


@router.get("/check-access")
@_catch
async def check_content_access(
        article_id: int = Query(..., description="文章ID"),
        required_level: int = Query(0, ge=0, le=10, description="所需VIP等级"),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(jwt_required)
):
    """检查当前用户对内容的访问权限"""
    service = create_membership_service(db)
    result = await service.check_content_access(current_user.id, article_id, required_level)
    return ok(data=result)


@router.post("/subscribe")
@_catch
async def create_subscription(
        request: CreateSubscriptionRequest,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """创建新订阅"""
    service = create_membership_service(db)
    result = await service.create_subscription(
        user_id=current_user.id,
        plan_id=request.plan_id,
        payment_amount=request.payment_amount,
        transaction_id=request.transaction_id,
    )
    if not result.get('success'):
        return fail(result.get('message', '订阅失败'))
    return ok(data=result, message="订阅成功")


@router.get("/plans")
@_catch
async def get_plans(
    db: AsyncSession = Depends(get_async_db)
):
    """获取所有可用 VIP 套餐"""
    service = create_membership_service(db)
    plans = await service.get_available_plans()
    return ok(data=plans)


@router.get("/features")
@_catch
async def get_features(
    db: AsyncSession = Depends(get_async_db)
):
    """获取所有 VIP 功能特权"""
    service = create_membership_service(db)
    features = await service.get_all_features()
    features_by_level = await service.get_features_by_level()
    return ok(data={
        'features': features,
        'features_by_level': features_by_level,
    })


@router.get("/my-subscription")
@_catch
async def get_my_subscription(
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """获取当前用户的订阅信息"""
    service = create_membership_service(db)
    status = await service.get_user_vip_status(current_user.id)
    history = await service.get_user_subscriptions(current_user.id)

    active_subscription = None
    if status.get('is_vip') and status.get('subscription_id'):
        for sub in history:
            if sub['id'] == status['subscription_id']:
                active_subscription = sub
                break

    return ok(data={
        'active_subscription': active_subscription,
        'subscription_history': history,
    })


@router.get("/premium-content")
@_catch
async def get_premium_content(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """获取需要 VIP 访问的文章列表"""
    service = create_membership_service(db)
    result = await service.get_premium_content(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return ok(data=result)
