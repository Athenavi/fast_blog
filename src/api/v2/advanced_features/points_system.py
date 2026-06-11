"""
用户积分系统 API
提供积分查询、兑换、排行榜等功能
"""
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.models.user import User as UserModel
from shared.services.advanced_features.points_system import points_system
from src.api.v2._helpers import ok, fail, _catch
from src.auth.auth_deps import get_current_active_user, admin_required as admin_required_api

router = APIRouter(tags=["points"])


@router.get("/my-points", summary="获取我的积分")
@_catch
async def get_my_points(current_user: UserModel = Depends(get_current_active_user)):
    """获取当前用户的积分余额"""
    points = points_system.get_user_points(current_user.id)
    return ok(data={'points': points})


@router.get("/my-stats", summary="获取我的积分统计")
@_catch
async def get_my_stats(current_user: UserModel = Depends(get_current_active_user)):
    """获取当前用户的积分统计数据"""
    stats = points_system.get_user_stats(current_user.id)
    return ok(data=stats)


@router.get("/my-history", summary="获取我的积分历史")
@_catch
async def get_my_history(
        limit: int = Query(50, ge=1, le=200, description="返回数量"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """获取当前用户的积分历史记录"""
    history = points_system.get_points_history(current_user.id, limit=limit)
    return ok(data={'history': history, 'count': len(history)})


@router.get("/leaderboard", summary="获取积分排行榜")
@_catch
async def get_leaderboard(
        limit: int = Query(100, ge=1, le=500, description="返回数量"),
        period: str = Query('all', enum=['all', 'week', 'month'], description="时间周期")
):
    """获取积分排行榜"""
    leaderboard = points_system.get_leaderboard(limit=limit, period=period)
    return ok(data={'leaderboard': leaderboard, 'count': len(leaderboard), 'period': period})


@router.get("/exchange-rules", summary="获取兑换规则")
@_catch
async def get_exchange_rules():
    """获取积分兑换规则"""
    rules = points_system.get_exchange_rules()
    return ok(data={'rules': rules})


@router.get("/points-rules", summary="获取积分规则")
@_catch
async def get_points_rules():
    """获取积分获取规则"""
    rules = points_system.get_points_rules()
    return ok(data={'rules': rules})


@router.post("/exchange", summary="积分兑换")
@_catch
async def exchange_points(
        item: str = Body(..., embed=True, description="兑换物品"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """使用积分兑换物品"""
    result = points_system.exchange_points(current_user.id, item)
    if result['success']:
        return ok(data={'item': result['item'], 'cost': result['cost'], 'remaining_points': result['remaining_points']},
                  message=result['message'])
    return fail(result['message'], data={'required': result.get('required'), 'current': result.get('current')})


@router.post("/record-action", summary="记录行为并发放积分")
@_catch
async def record_action(
        action: str = Body(..., embed=True, description="行为类型"),
        article_id: Optional[int] = Body(None, description="文章ID"),
        comment_id: Optional[int] = Body(None, description="评论ID"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """记录用户行为并自动发放积分"""
    success = points_system.record_action(current_user.id, action, article_id=article_id, comment_id=comment_id)
    if success:
        current_points = points_system.get_user_points(current_user.id)
        return ok(data={'action': action, 'current_points': current_points}, message='积分已发放')
    return fail('未获得积分(可能已达上限或重复操作)')


@router.post("/admin/add-points", summary="手动添加积分")
@_catch
async def admin_add_points(
        user_id: int = Body(..., description="目标用户ID"),
        points: int = Body(..., ge=1, description="积分数量"),
        reason: str = Body('', description="原因说明"),
        current_user: UserModel = Depends(admin_required_api)
):
    """管理员手动为用户添加积分"""
    success = points_system.add_points(user_id, points, f"Admin: {reason}")
    if success:
        return ok(data={'user_id': user_id, 'points_added': points, 'new_balance': points_system.get_user_points(user_id)},
                  message=f'成功为用户 {user_id} 添加 {points} 积分')
    return fail('添加失败')


@router.post("/admin/deduct-points", summary="手动扣除积分")
@_catch
async def admin_deduct_points(
        user_id: int = Body(..., description="目标用户ID"),
        points: int = Body(..., ge=1, description="积分数量"),
        reason: str = Body('', description="原因说明"),
        current_user: UserModel = Depends(admin_required_api)
):
    """管理员手动扣除用户积分"""
    success = points_system.deduct_points(user_id, points, f"Admin: {reason}")
    if success:
        return ok(data={'user_id': user_id, 'points_deducted': points, 'new_balance': points_system.get_user_points(user_id)},
                  message=f'成功从用户 {user_id} 扣除 {points} 积分')
    return fail('扣除失败(积分不足)')


@router.get("/admin/stats", summary="获取积分系统统计")
@_catch
async def get_system_stats(current_user: UserModel = Depends(admin_required_api)):
    """获取积分系统整体统计"""
    total_users_with_points = len([uid for uid, p in points_system._user_points.items() if p > 0])
    total_points_issued = sum(points_system._user_points.values())
    return ok(data={'total_users_with_points': total_users_with_points, 'total_points_issued': total_points_issued})
