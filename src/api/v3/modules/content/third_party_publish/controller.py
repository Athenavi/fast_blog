"""third_party_publish 模块路由（content 域：多平台发布底座）

::

    # 渠道配置（凭据加密存储、永不回传）
    GET    /api/v3/content/third-party-publish/channel                  渠道列表
    POST   /api/v3/content/third-party-publish/channel                  新建渠道
    GET    /api/v3/content/third-party-publish/channel/{channel_id}     渠道详情
    PUT    /api/v3/content/third-party-publish/channel/{channel_id}     更新渠道（凭据留空=保持原值）
    DELETE /api/v3/content/third-party-publish/channel/{channel_id}     删除渠道（级联删任务/日志）
    POST   /api/v3/content/third-party-publish/channel/{channel_id}/verify  凭据/连通性自检

    # 平台
    GET    /api/v3/content/third-party-publish/platform                已注册适配器的平台清单

    # 发布任务
    GET    /api/v3/content/third-party-publish/task                     任务列表
    POST   /api/v3/content/third-party-publish/task                     创建任务（创建后立即尝试执行）
    GET    /api/v3/content/third-party-publish/task/{task_id}           任务详情（含载荷快照 + 最近日志）
    DELETE /api/v3/content/third-party-publish/task/{task_id}           删除任务
    POST   /api/v3/content/third-party-publish/task/{task_id}/retry     手动重试
    GET    /api/v3/content/third-party-publish/task/{task_id}/log       任务的尝试记录

权限码：``module_content:third_party_publish:{view,create,edit,delete,execute}``。

**底座 vs 适配器**：渠道配置 / 任务 / 记录 / 重试这些底座能力本期完整可用；
"往某个平台真发内容"由适配器完成，**按平台清单分期接入**（当前注册表为空）。
没有适配器的平台，任务会如实落在 ``failed`` 并写明原因 —— 不存在假装成功的路径。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.third_party_publish.adapters import adapter_platforms
from src.api.v3.modules.content.third_party_publish.schema import (
    PublishChannelCreate,
    PublishChannelUpdate,
    PublishTaskCreate,
)
from src.api.v3.modules.content.third_party_publish.service import (
    publish_channel_service,
    publish_task_service,
)

router = APIRouter(
    prefix="/third-party-publish",
    tags=["content-third-party-publish"],
    route_class=OperationLogRoute,
)


# ---------------------------------------------------------------- 平台
@router.get("/platform", response_model=ResponseModel, summary="已接入的平台适配器清单")
async def list_platforms(
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_VIEW),
) -> dict:
    """返回**已注册适配器**的平台；空列表表示平台适配器尚未接入（底座可用）。"""
    items = adapter_platforms()
    return resp.success({"items": items, "total": len(items)})


# ---------------------------------------------------------------- 渠道
@router.get("/channel", response_model=ResponseModel, summary="发布渠道列表")
async def list_channels(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    platform: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await publish_channel_service.list_channels(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        platform=platform,
        is_active=is_active,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/channel", response_model=ResponseModel, summary="新建发布渠道")
async def create_channel(
    payload: PublishChannelCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_CREATE),
) -> dict:
    return resp.success(
        await publish_channel_service.create_channel(db, payload, user_id=current.id),
        msg="已创建",
    )


@router.get("/channel/{channel_id}", response_model=ResponseModel, summary="渠道详情")
async def get_channel(
    channel_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_VIEW),
) -> dict:
    return resp.success(await publish_channel_service.get_channel(db, channel_id))


@router.put("/channel/{channel_id}", response_model=ResponseModel, summary="更新发布渠道")
async def update_channel(
    channel_id: int,
    payload: PublishChannelUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_EDIT),
) -> dict:
    return resp.success(
        await publish_channel_service.update_channel(db, channel_id, payload), msg="已保存"
    )


@router.delete("/channel/{channel_id}", response_model=ResponseModel, summary="删除发布渠道")
async def delete_channel(
    channel_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_DELETE),
) -> dict:
    await publish_channel_service.delete_channel(db, channel_id)
    return resp.success(None, msg="已删除")


@router.post("/channel/{channel_id}/verify", response_model=ResponseModel, summary="渠道凭据自检")
async def verify_channel(
    channel_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_EDIT),
) -> dict:
    """调用适配器的 ``verify``（不产生对外发布）；平台未接入则 400 并说明原因。"""
    return resp.success(await publish_channel_service.verify_channel(db, channel_id))


# ---------------------------------------------------------------- 任务
@router.get("/task", response_model=ResponseModel, summary="发布任务列表")
async def list_tasks(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    article_id: Optional[int] = Query(default=None),
    channel_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None, description="pending/publishing/success/failed"),
) -> dict:
    items, total = await publish_task_service.list_tasks(
        db,
        page=page,
        page_size=page_size,
        article_id=article_id,
        channel_id=channel_id,
        status=status,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/task", response_model=ResponseModel, summary="创建发布任务")
async def create_task(
    payload: PublishTaskCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_CREATE),
) -> dict:
    """创建后**立即尝试执行**；同一 (文章, 渠道) 已有任务时复用原任务（幂等）。"""
    detail, created = await publish_task_service.create_task(db, payload, user_id=current.id)
    msg = "已创建" if created else "该文章在该渠道已有发布任务，已返回原任务"
    return resp.success(detail, msg=msg)


@router.get("/task/{task_id}", response_model=ResponseModel, summary="发布任务详情")
async def get_task(
    task_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_VIEW),
) -> dict:
    return resp.success(await publish_task_service.get_task(db, task_id))


@router.delete("/task/{task_id}", response_model=ResponseModel, summary="删除发布任务")
async def delete_task(
    task_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_DELETE),
) -> dict:
    await publish_task_service.delete_task(db, task_id)
    return resp.success(None, msg="已删除")


@router.post("/task/{task_id}/retry", response_model=ResponseModel, summary="手动重试发布")
async def retry_task(
    task_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_EXECUTE),
) -> dict:
    """用**创建时冻结的载荷快照**重试；失败仍如实落 ``failed`` + 日志。"""
    return resp.success(await publish_task_service.retry_task(db, task_id), msg="已重试")


@router.get("/task/{task_id}/log", response_model=ResponseModel, summary="发布尝试记录")
async def list_logs(
    task_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.THIRD_PARTY_PUBLISH_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await publish_task_service.list_logs(
        db, task_id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)
