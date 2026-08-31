"""
会员订阅 API - 统一会员/VIP功能模块
整合了原有的 vip.py 和 membership.py 功能
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from shared.services.core.membership import create_membership_service
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["membership"])

# ─── 支付网关集成 ─────────────────────────────
PAYMENT_PLUGIN_SLUG = "payment-gateway"


def _get_payment_plugin():
    """获取支付网关插件实例（如果已安装激活）"""
    try:
        from shared.services.plugins.plugin_manager import plugin_manager
        plugin = plugin_manager.get_plugin(PAYMENT_PLUGIN_SLUG)
        if plugin and plugin.active:
            return plugin
    except Exception:
        pass
    return None


class CreateSubscriptionRequest(BaseModel):
    """创建订阅请求"""
    plan_id: int
    payment_amount: float
    transaction_id: Optional[str] = None


class CreatePaymentRequest(BaseModel):
    """创建支付请求"""
    plan_id: int = Field(..., description="套餐ID")
    provider: Optional[str] = Field(None, description="支付服务商，如 alipay/wechat/stripe，为空则使用插件默认")
    return_url: Optional[str] = Field(None, description="支付成功后的前端跳转URL")
    notify_url: Optional[str] = Field(None, description="支付回调通知URL")


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


@router.post("/create-payment")
@_catch
async def create_payment(
        request: CreatePaymentRequest,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """创建支付订单（通过支付网关插件）"""
    # 获取套餐信息
    service = create_membership_service(db)
    plans = await service.get_available_plans()
    plan = next((p for p in plans if p.get('id') == request.plan_id), None)
    if not plan:
        return fail("套餐不存在")

    # 尝试使用支付网关插件
    plugin = _get_payment_plugin()
    if plugin:
        # 设置提供商
        if request.provider:
            plugin.settings['provider'] = request.provider

        order_id = f"VIP_{current_user.id}_{request.plan_id}_{int(__import__('time').time())}"
        amount = int(float(plan.get('price', 0)) * 100)  # 转换为分

        result = plugin.create_payment(
            order_id=order_id,
            amount=amount,
            subject=f"VIP {plan.get('name', '')}",
            user_id=current_user.id,
            return_url=request.return_url or "",
            notify_url=request.notify_url or "",
        )
        if result.get('success'):
            return ok(data={
                'order_id': order_id,
                'payment_url': result.get('payment_url'),
                'prepay_id': result.get('prepay_id'),
                'provider': result.get('provider'),
                'amount': amount,
                'plan_id': request.plan_id,
            })
        return fail(result.get('error', '创建支付失败'))
    else:
        # 支付网关插件未安装，返回支付信息供前端自行处理
        return ok(data={
            'order_id': None,
            'payment_url': None,
            'provider': None,
            'amount': int(float(plan.get('price', 0)) * 100),
            'plan_id': request.plan_id,
            'note': 'Payment gateway plugin not available',
        })


@router.post("/subscribe")
@_catch
async def create_subscription(
        request: CreateSubscriptionRequest,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """创建新订阅（支付确认后调用）"""
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
