"""
打赏系统 API
提供文章打赏、统计、排行榜等功能
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.models.user import User as UserModel
from shared.services.ecommerce.tipping_system import tipping_system
from src.api.v2._helpers import ok, fail, _catch
from src.auth.auth_deps import get_current_active_user

router = APIRouter(tags=["tips"])


@router.post("/tip-article", summary="打赏文章")
@_catch
async def tip_article(
        article_id: int = Body(..., description="文章ID"),
        amount: float = Body(..., ge=1, le=10000, description="打赏金额"),
        message: str = Body('', description="留言(可选)"),
        payment_method: str = Body('balance', enum=['balance', 'wechat', 'alipay'], description="支付方式"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """对文章进行打赏"""
    article_author_id = 1
    if article_author_id == current_user.id:
        return fail('不能打赏自己的文章')

    tip = tipping_system.create_tip(
        from_user_id=current_user.id, to_user_id=article_author_id,
        article_id=article_id, amount=amount, message=message,
        payment_method=payment_method,
    )
    return ok(data={'tip_id': tip['tip_id'], 'amount': tip['amount'], 'to_user_id': tip['to_user_id']},
              message='打赏成功')


@router.get("/article/{article_id}", summary="获取文章打赏记录")
@_catch
async def get_article_tips(
        article_id: int,
        limit: int = Query(50, ge=1, le=200, description="返回数量")
):
    """获取文章的打赏记录列表"""
    tips = tipping_system.get_article_tips(article_id, limit=limit)
    stats = tipping_system.get_article_tip_stats(article_id)
    return ok(data={'tips': tips, 'stats': stats, 'count': len(tips)})


@router.get("/my-received", summary="获取我收到的打赏")
@_catch
async def get_my_received_tips(
        limit: int = Query(100, ge=1, le=500, description="返回数量"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """获取当前用户收到的打赏记录"""
    tips = tipping_system.get_user_received_tips(current_user.id, limit=limit)
    stats = tipping_system.get_user_tip_stats(current_user.id)
    return ok(data={'tips': tips, 'stats': stats, 'count': len(tips)})


@router.get("/my-stats", summary="获取我的打赏统计")
@_catch
async def get_my_tip_stats(current_user: UserModel = Depends(get_current_active_user)):
    """获取当前用户的打赏统计数据"""
    stats = tipping_system.get_user_tip_stats(current_user.id)
    return ok(data=stats)


@router.get("/leaderboard", summary="获取打赏排行榜")
@_catch
async def get_tipping_leaderboard(
        period: str = Query('all', enum=['all', 'month', 'week'], description="时间周期"),
        limit: int = Query(100, ge=1, le=500, description="返回数量")
):
    """获取打赏排行榜"""
    leaderboard = tipping_system.get_tipping_leaderboard(period=period, limit=limit)
    return ok(data={'leaderboard': leaderboard, 'count': len(leaderboard), 'period': period})


@router.get("/preset-amounts", summary="获取预设打赏金额")
@_catch
async def get_preset_amounts():
    """获取系统预设的打赏金额选项"""
    amounts = tipping_system.get_preset_amounts()
    return ok(data={'amounts': amounts, 'min_amount': tipping_system.min_amount, 'max_amount': tipping_system.max_amount})


@router.get("/recent", summary="获取最近打赏记录")
@_catch
async def get_recent_tips(limit: int = Query(20, ge=1, le=100, description="返回数量")):
    """获取全站最近的打赏记录"""
    tips = tipping_system.get_recent_tips(limit=limit)
    return ok(data={'tips': tips, 'count': len(tips)})


@router.post("/refund", summary="退款打赏")
@_catch
async def refund_tip(
        tip_id: str = Body(..., description="打赏ID"),
        reason: str = Body('', description="退款原因"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """申请退款打赏"""
    success = tipping_system.refund_tip(tip_id, reason)
    if success:
        return ok(data={'tip_id': tip_id}, message='退款成功')
    return fail('退款失败(打赏不存在或已退款)')


@router.get("/balance", summary="获取可提现余额")
@_catch
async def get_available_balance(current_user: UserModel = Depends(get_current_active_user)):
    """获取当前用户的可提现余额信息"""
    balance_info = tipping_system.get_user_available_balance(current_user.id)
    return ok(data=balance_info)


@router.post("/withdraw", summary="申请提现")
@_catch
async def request_withdrawal(
        amount: float = Body(..., ge=1, description="提现金额"),
        payment_method: str = Body('bank_transfer', enum=['bank_transfer', 'wechat', 'alipay'], description="支付方式"),
        account_info: dict = Body({}, description="账户信息"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """申请提现"""
    withdrawal = tipping_system.create_withdrawal(
        user_id=current_user.id, amount=amount,
        payment_method=payment_method, account_info=account_info,
    )
    return ok(data={
        'withdrawal_id': withdrawal['withdrawal_id'], 'amount': withdrawal['amount'],
        'fee': withdrawal['fee'], 'actual_amount': withdrawal['actual_amount'],
        'status': withdrawal['status'],
    }, message='提现申请已提交')


@router.get("/my-withdrawals", summary="获取我的提现记录")
@_catch
async def get_my_withdrawals(
        limit: int = Query(50, ge=1, le=200, description="返回数量"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """获取当前用户的提现记录"""
    withdrawals = tipping_system.get_user_withdrawals(current_user.id, limit=limit)
    return ok(data={'withdrawals': withdrawals, 'count': len(withdrawals)})


@router.post("/cancel-withdrawal/{withdrawal_id}", summary="取消提现申请")
@_catch
async def cancel_withdrawal(
        withdrawal_id: str,
        current_user: UserModel = Depends(get_current_active_user)
):
    """取消提现申请（仅限pending状态）"""
    success = tipping_system.cancel_withdrawal(withdrawal_id, current_user.id)
    if success:
        return ok(data=None, message='提现申请已取消')
    return fail('取消失败(提现不存在或状态不允许取消)')


@router.post("/admin/process-withdrawal", summary="处理提现申请（管理员）")
@_catch
async def admin_process_withdrawal(
        withdrawal_id: str = Body(..., description="提现ID"),
        status: str = Body('completed', enum=['completed', 'rejected'], description="处理结果"),
        admin_note: str = Body('', description="管理员备注"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """管理员处理提现申请"""
    success = tipping_system.process_withdrawal(
        withdrawal_id=withdrawal_id, status=status, admin_note=admin_note,
    )
    if success:
        msg = '通过' if status == 'completed' else '拒绝'
        return ok(data=None, message=f'提现申请已{msg}')
    return fail('处理失败(提现不存在或状态不允许处理)')
