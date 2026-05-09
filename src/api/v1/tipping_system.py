"""
打赏系统 API
提供文章打赏、统计、排行榜等功能
"""

from fastapi import APIRouter, Depends, Query, Body

from src.auth.auth_deps import get_current_active_user
from shared.models.user import User as UserModel
from shared.utils.response import ApiResponse
from shared.services.tipping_system import tipping_system

router = APIRouter(prefix="/tips", tags=["tips"])


@router.post("/tip-article", summary="打赏文章")
async def tip_article(
        article_id: int = Body(..., description="文章ID"),
        amount: float = Body(..., ge=1, le=10000, description="打赏金额"),
        message: str = Body('', description="留言(可选)"),
        payment_method: str = Body('balance', enum=['balance', 'wechat', 'alipay'], description="支付方式"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    对文章进行打赏
    
    Args:
        article_id: 文章ID
        amount: 打赏金额(1-10000)
        message: 留言(可选)
        payment_method: 支付方式(balance/wechat/alipay)
        
    Returns:
        打赏结果
    """
    try:
        # TODO: 从数据库获取文章作者ID
        # 这里使用模拟数据
        article_author_id = 1  # 假设文章作者是用户1

        if article_author_id == current_user.id:
            return ApiResponse(success=False, error='不能打赏自己的文章')

        # 创建打赏
        tip = tipping_system.create_tip(
            from_user_id=current_user.id,
            to_user_id=article_author_id,
            article_id=article_id,
            amount=amount,
            message=message,
            payment_method=payment_method,
        )

        return ApiResponse(
            success=True,
            message='打赏成功',
            data={
                'tip_id': tip['tip_id'],
                'amount': tip['amount'],
                'to_user_id': tip['to_user_id'],
            }
        )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=f"打赏失败: {str(e)}")


@router.get("/article/{article_id}", summary="获取文章打赏记录")
async def get_article_tips(
        article_id: int,
        limit: int = Query(50, ge=1, le=200, description="返回数量")
):
    """
    获取文章的打赏记录列表
    
    Args:
        article_id: 文章ID
        limit: 返回数量(1-200)
        
    Returns:
        打赏记录列表
    """
    try:
        tips = tipping_system.get_article_tips(article_id, limit=limit)
        stats = tipping_system.get_article_tip_stats(article_id)

        return ApiResponse(
            success=True,
            data={
                'tips': tips,
                'stats': stats,
                'count': len(tips),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取打赏记录失败: {str(e)}")


@router.get("/my-received", summary="获取我收到的打赏")
async def get_my_received_tips(
        limit: int = Query(100, ge=1, le=500, description="返回数量"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    获取当前用户收到的打赏记录
    
    Args:
        limit: 返回数量(1-500)
        
    Returns:
        打赏记录列表
    """
    try:
        tips = tipping_system.get_user_received_tips(current_user.id, limit=limit)
        stats = tipping_system.get_user_tip_stats(current_user.id)

        return ApiResponse(
            success=True,
            data={
                'tips': tips,
                'stats': stats,
                'count': len(tips),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取打赏记录失败: {str(e)}")


@router.get("/my-stats", summary="获取我的打赏统计")
async def get_my_tip_stats(
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    获取当前用户的打赏统计数据
    
    Returns:
        统计数据
    """
    try:
        stats = tipping_system.get_user_tip_stats(current_user.id)

        return ApiResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取统计失败: {str(e)}")


@router.get("/leaderboard", summary="获取打赏排行榜")
async def get_tipping_leaderboard(
        period: str = Query('all', enum=['all', 'month', 'week'], description="时间周期"),
        limit: int = Query(100, ge=1, le=500, description="返回数量")
):
    """
    获取打赏排行榜(按收到打赏金额排序)
    
    Args:
        period: 时间周期(all/month/week)
        limit: 返回数量(1-500)
        
    Returns:
        排行榜列表
    """
    try:
        leaderboard = tipping_system.get_tipping_leaderboard(period=period, limit=limit)

        return ApiResponse(
            success=True,
            data={
                'leaderboard': leaderboard,
                'count': len(leaderboard),
                'period': period,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取排行榜失败: {str(e)}")


@router.get("/preset-amounts", summary="获取预设打赏金额")
async def get_preset_amounts():
    """
    获取系统预设的打赏金额选项
    
    Returns:
        金额列表
    """
    try:
        amounts = tipping_system.get_preset_amounts()

        return ApiResponse(
            success=True,
            data={
                'amounts': amounts,
                'min_amount': tipping_system.min_amount,
                'max_amount': tipping_system.max_amount,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取金额失败: {str(e)}")


@router.get("/recent", summary="获取最近打赏记录")
async def get_recent_tips(
        limit: int = Query(20, ge=1, le=100, description="返回数量")
):
    """
    获取全站最近的打赏记录
    
    Args:
        limit: 返回数量(1-100)
        
    Returns:
        打赏记录列表
    """
    try:
        tips = tipping_system.get_recent_tips(limit=limit)

        return ApiResponse(
            success=True,
            data={
                'tips': tips,
                'count': len(tips),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取记录失败: {str(e)}")


@router.post("/refund", summary="退款打赏")
async def refund_tip(
        tip_id: str = Body(..., description="打赏ID"),
        reason: str = Body('', description="退款原因"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """
    申请退款打赏
    
    Args:
        tip_id: 打赏ID
        reason: 退款原因
        
    Returns:
        退款结果
    """
    try:
        # TODO: 验证用户是否有权限退款(打赏者或文章作者)
        success = tipping_system.refund_tip(tip_id, reason)

        if success:
            return ApiResponse(
                success=True,
                message='退款成功',
                data={
                    'tip_id': tip_id,
                }
            )
        else:
            return ApiResponse(success=False, error='退款失败(打赏不存在或已退款)')
    except Exception as e:
        return ApiResponse(success=False, error=f"退款失败: {str(e)}")
