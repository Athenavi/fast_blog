"""mobile.revenue 模块路由（前台用户端：我的收益）

::

    GET  /api/v3/mobile/revenue/record   我的收益记录（分页）
    GET  /api/v3/mobile/revenue/stats    我的收益汇总（含统计快照）
    POST /api/v3/mobile/revenue/payout   发起提现申请

鉴权：**仅需认证**（无权限码，已登记进 ``audit.EXEMPT_WRITE_ENDPOINTS``），
``user_id`` 一律取登录用户；发起提现只操作本人数据，越权无处可传。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.mobile.revenue.schema import MobilePayoutCreate
from src.api.v3.modules.mobile.revenue.service import mobile_revenue_service

router = APIRouter(prefix="/revenue", tags=["mobile-revenue"], route_class=OperationLogRoute)


@router.get("/record", response_model=ResponseModel, summary="我的收益记录")
async def my_records(
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await mobile_revenue_service.list_records(
        db, current.id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/stats", response_model=ResponseModel, summary="我的收益汇总")
async def my_stats(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await mobile_revenue_service.summary(db, current.id))


@router.post("/payout", response_model=ResponseModel, summary="发起提现申请")
async def create_my_payout(
    payload: MobilePayoutCreate,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    return resp.success(
        await mobile_revenue_service.create_payout(db, current.id, payload), msg="已提交"
    )
