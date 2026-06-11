"""
会员订阅 API - 统一会员/VIP功能模块
整合了原有的 vip.py 和 membership.py 功能
"""
from datetime import datetime
from functools import wraps
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import VIPSubscription
from shared.models.article import Article
from shared.models.user import User
from shared.models.vip import VIPFeature
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
        user_id: int = Query(..., description="用户ID"),
        article_id: int = Query(..., description="文章ID"),
        required_level: int = Query(0, ge=0, le=10, description="所需VIP等级"),
        db: AsyncSession = Depends(get_async_db)
):
    """检查内容访问权限"""
    service = create_membership_service(db)
    result = await service.check_content_access(user_id, article_id, required_level)
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
    subscription = await service.create_subscription(
        user_id=current_user.id,
        plan_id=request.plan_id,
        payment_amount=request.payment_amount,
        transaction_id=request.transaction_id,
    )
    return ok(data=subscription.to_dict(), message="订阅成功")
