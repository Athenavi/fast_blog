"""points 模块路由（gamification 域：积分）

::

    GET  /api/v3/gamification/points/mine              我的积分账户（仅认证）
    GET  /api/v3/gamification/points/history           我的积分流水（仅认证）
    POST /api/v3/gamification/points/checkin           每日签到（仅认证，幂等）
    POST /api/v3/gamification/points/exchange          兑换（仅认证，真实开通 VIP）
    GET  /api/v3/gamification/points/leaderboard       排行榜（公开）
    GET  /api/v3/gamification/points/rules             积分规则（公开）
    GET  /api/v3/gamification/points/exchange-rules    兑换项（公开）
    GET  /api/v3/gamification/points/stats             管理统计
    POST /api/v3/gamification/points/grant             管理员加分
    POST /api/v3/gamification/points/deduct            管理员扣分
    PUT  /api/v3/gamification/points/rule/{rule_id}    更新规则

权限码：``module_gamification:points:{view,edit}``。

**刻意没有 v2 的 `POST /record-action`** —— v2 让前端自报动作加分（任何登录用户可刷分）。
这里第一期只保留每日签到与管理端加减分（写操作已登记 `audit.EXEMPT_WRITE_ENDPOINTS`：
签到/兑换都只操作**本人**数据）。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.gamification.points.schema import (
    ExchangeRequest,
    PointsGrantRequest,
    PointsRuleUpdate,
)
from src.api.v3.modules.gamification.points.service import points_service

router = APIRouter(prefix="/points", tags=["gamification-points"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 我的
@router.get("/mine", response_model=ResponseModel, summary="我的积分账户")
async def my_points(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await points_service.account(db, current.id))


@router.get("/history", response_model=ResponseModel, summary="我的积分流水")
async def my_history(
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await points_service.history(
        db, current.id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/checkin", response_model=ResponseModel, summary="每日签到")
async def checkin(db: DBSession, current: CurrentUser) -> dict:
    """幂等：今天已签到会返回 400（而不是静默重复加分）"""
    return resp.success(await points_service.checkin(db, current.id), msg="签到成功")


@router.post("/exchange", response_model=ResponseModel, summary="积分兑换")
async def exchange(payload: ExchangeRequest, db: DBSession, current: CurrentUser) -> dict:
    """**真实发放**：扣分 + 写流水 + 调 MembershipService 开通套餐（不是只记一笔待发放）"""
    return resp.success(await points_service.exchange(db, current.id, payload), msg="兑换成功")


# ---------------------------------------------------------------- 公开
@router.get("/leaderboard", response_model=ResponseModel, summary="积分排行榜")
async def leaderboard(
    db: DBSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """公开读：排行榜按余额倒序（真实聚合，不是占位）"""
    return resp.success(await points_service.leaderboard(db, limit=limit))


@router.get("/rules", response_model=ResponseModel, summary="积分规则")
async def list_rules(db: DBSession) -> dict:
    return resp.success(await points_service.rules(db, exchange=False))


@router.get("/exchange-rules", response_model=ResponseModel, summary="兑换项")
async def list_exchange_rules(db: DBSession) -> dict:
    return resp.success(await points_service.rules(db, exchange=True))


# ---------------------------------------------------------------- 管理端
@router.get("/stats", response_model=ResponseModel, summary="积分统计")
async def points_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.POINTS_VIEW),
) -> dict:
    return resp.success(await points_service.stats(db))


@router.post("/grant", response_model=ResponseModel, summary="管理员加分")
async def grant_points(
    payload: PointsGrantRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.POINTS_EDIT),
) -> dict:
    return resp.success(await points_service.grant(db, payload, current.id), msg="已加分")


@router.post("/deduct", response_model=ResponseModel, summary="管理员扣分")
async def deduct_points(
    payload: PointsGrantRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.POINTS_EDIT),
) -> dict:
    return resp.success(await points_service.deduct(db, payload, current.id), msg="已扣分")


@router.put("/rule/{rule_id}", response_model=ResponseModel, summary="更新积分规则")
async def update_rule(
    rule_id: int,
    payload: PointsRuleUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.POINTS_EDIT),
) -> dict:
    return resp.success(await points_service.update_rule(db, rule_id, payload), msg="已保存")
