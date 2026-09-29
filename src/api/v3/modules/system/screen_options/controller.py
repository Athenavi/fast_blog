"""screen_options 模块路由（用户级屏幕选项 / 每页 UI 偏好）

::

    GET    /api/v3/system/screen-options                 全部页面的偏好（按 page 分组）
    GET    /api/v3/system/screen-options/{page}          单页偏好（缺省项用默认值补齐）
    PUT    /api/v3/system/screen-options/{page}          整体覆盖单页偏好
    PATCH  /api/v3/system/screen-options/{page}/{key}    修改单项
    DELETE /api/v3/system/screen-options/{page}/{key}    删除单项
    DELETE /api/v3/system/screen-options/{page}          删除整页
    DELETE /api/v3/system/screen-options                 重置全部

全部端点**只需登录**：操作对象恒为当前登录用户自己的偏好，接口不接受 ``user_id``
参数——越权无处可传。偏好落 ``system_settings``（键 ``screen_options.{user_id}``）。
"""

from typing import Any, Dict

from fastapi import APIRouter, Body

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.screen_options.schema import OptionValueUpdate
from src.api.v3.modules.system.screen_options.service import screen_options_service

router = APIRouter(
    prefix="/screen-options",
    tags=["system-screen-options"],
    route_class=OperationLogRoute,
)


@router.get("", response_model=ResponseModel, summary="全部屏幕选项（按页面分组）")
async def get_all_options(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await screen_options_service.get_all(db, current.id))


@router.get("/{page}", response_model=ResponseModel, summary="单页屏幕选项")
async def get_page_options(page: str, db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await screen_options_service.get_page(db, current.id, page))


@router.put("/{page}", response_model=ResponseModel, summary="整体覆盖单页屏幕选项")
async def set_page_options(
    page: str,
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="整页偏好；未知 page 会自动新建。收原始 dict，避免 pydantic 静默丢弃未知键",
        examples=[
            {"columns": ["title", "status"], "per_page": 50, "order_by": "created_at"}
        ],
    ),
) -> dict:
    return resp.success(
        await screen_options_service.set_page(db, current.id, page, payload),
        msg="已保存",
    )


@router.patch("/{page}/{key}", response_model=ResponseModel, summary="修改单页的某个选项")
async def patch_option(
    page: str,
    key: str,
    payload: OptionValueUpdate,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    return resp.success(
        await screen_options_service.patch_option(
            db, current.id, page, key, payload.value
        ),
        msg="已更新",
    )


@router.delete("/{page}/{key}", response_model=ResponseModel, summary="删除单页的某个选项")
async def delete_option(
    page: str, key: str, db: DBSession, current: CurrentUser
) -> dict:
    return resp.success(
        await screen_options_service.delete_option(db, current.id, page, key),
        msg="已删除",
    )


@router.delete("/{page}", response_model=ResponseModel, summary="删除整页屏幕选项")
async def delete_page(page: str, db: DBSession, current: CurrentUser) -> dict:
    await screen_options_service.delete_page(db, current.id, page)
    return resp.success(None, msg="已删除")


@router.delete("", response_model=ResponseModel, summary="重置全部屏幕选项")
async def reset_options(db: DBSession, current: CurrentUser) -> dict:
    removed = await screen_options_service.reset(db, current.id)
    return resp.success({"removed_pages": removed}, msg="已重置")
