"""feed 模块路由（前台用户端：关注流 personalized feed）

::

    GET /api/v3/mobile/feed   我的关注流（分页）

鉴权：**仅需认证**（``CurrentUser``），无权限码——只读本人关注关系聚合成文章，
不操作任何数据，``user_id`` 一律取登录用户，越权无处可传。

> 关注为空时返回**空页**（不是报错，也**不**退化成全站文章）；
> ``page_size`` 上限 50（比通用列表的 100 小：关注流首屏更小）。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.mobile.feed.service import feed_service

router = APIRouter(prefix="/feed", tags=["mobile-feed"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="我的关注流")
async def my_feed(
    db: DBSession,
    current: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> dict:
    items, total = await feed_service.list_feed(db, current.id, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)
