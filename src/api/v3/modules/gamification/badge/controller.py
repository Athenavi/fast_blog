"""badge 模块路由（gamification 域：勋章）

::

    GET  /api/v3/gamification/badge/mine                    我的勋章（仅认证）
    GET  /api/v3/gamification/badge/available               全部可获得（公开）
    GET  /api/v3/gamification/badge/categories              分类（公开）
    GET  /api/v3/gamification/badge/details/{badge_key}     勋章详情（公开）
    GET  /api/v3/gamification/badge/progress/{badge_key}    我的进度（仅认证）
    POST /api/v3/gamification/badge/check-and-award         检查并授予（仅认证，幂等）
    POST /api/v3/gamification/badge/award                   手工授予（管理员）
    GET  /api/v3/gamification/badge/stats                   勋章统计（管理员）

权限码：``module_gamification:badge:{view,edit}``。

``check-and-award`` 是写操作但**仅操作本人**（写操作已登记
`audit.EXEMPT_WRITE_ENDPOINTS`）；它**幂等**：已拥有的跳过、``is_manual`` 的不自动授予。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.gamification.badge.schema import BadgeAwardRequest
from src.api.v3.modules.gamification.badge.service import badge_service

router = APIRouter(prefix="/badge", tags=["gamification-badge"], route_class=OperationLogRoute)


@router.get("/mine", response_model=ResponseModel, summary="我的勋章")
async def my_badges(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await badge_service.user_badges(db, current.id))


@router.get("/available", response_model=ResponseModel, summary="全部可获得勋章")
async def available_badges(
    db: DBSession,
    category: Optional[str] = Query(default=None),
) -> dict:
    """公开：勋章定义（含条件与奖励）"""
    return resp.success(await badge_service.available(db, category=category))


@router.get("/categories", response_model=ResponseModel, summary="勋章分类")
async def badge_categories(db: DBSession) -> dict:
    return resp.success(await badge_service.categories(db))


@router.get("/details/{badge_key}", response_model=ResponseModel, summary="勋章详情")
async def badge_details(badge_key: str, db: DBSession) -> dict:
    return resp.success(await badge_service.details(db, badge_key))


@router.get("/progress/{badge_key}", response_model=ResponseModel, summary="我的勋章进度")
async def badge_progress(badge_key: str, db: DBSession, current: CurrentUser) -> dict:
    """真实统计对比阈值（v2 的统计恒为 0，进度永远是 0%）"""
    return resp.success(await badge_service.progress(db, current.id, badge_key))


@router.post("/check-and-award", response_model=ResponseModel, summary="检查并授予勋章")
async def check_and_award(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await badge_service.check_and_award(db, current.id), msg="已检查")


@router.post("/award", response_model=ResponseModel, summary="手工授予勋章")
async def award_badge(
    payload: BadgeAwardRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.BADGE_EDIT),
) -> dict:
    return resp.success(await badge_service.award(db, payload, current.id), msg="已授予")


@router.get("/stats", response_model=ResponseModel, summary="勋章统计")
async def badge_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.BADGE_VIEW),
) -> dict:
    return resp.success(await badge_service.stats(db))
