"""setting 模块路由

RESTful 主路径::

    GET    /api/v3/system/setting              配置列表
    GET    /api/v3/system/setting/public       公开配置（无需鉴权，供前端初始化）
    GET    /api/v3/system/setting/{key}        单项配置
    PUT    /api/v3/system/setting              批量写入
    PUT    /api/v3/system/setting/{key}        写入单项
    DELETE /api/v3/system/setting/{key}        删除单项

``/public`` 是静态路径，必须注册在 ``/{key}`` 之前（由 ``assert_no_shadowed_routes`` 强制）。

权限码：``settings:view`` / ``settings:edit``
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.setting.schema import (
    SettingBatchUpsert,
    SettingUpsert,
    SettingValueUpdate,
)
from src.api.v3.modules.system.setting.service import setting_service

router = APIRouter(prefix="/setting", tags=["system-setting"], route_class=OperationLogRoute)


# ─────────────────────────── 公开配置（无鉴权）───────────────────────────
@router.get("/public", response_model=ResponseModel, summary="公开配置（无需鉴权）")
async def public_settings(db: DBSession) -> dict:
    return resp.success(await setting_service.public_settings(db))


# ─────────────────────────── 列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="配置列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 配置列表",
)
async def list_settings(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
    is_public: Optional[bool] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items = await setting_service.list_settings(db, is_public=is_public, keyword=keyword)
    return resp.success_page(items, len(items), 1, len(items) or 1)


# ─────────────────────────── 批量写入 ───────────────────────────
@router.put("", response_model=ResponseModel, summary="批量写入配置")
async def batch_upsert_settings(
    payload: SettingBatchUpsert,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    return resp.success(await setting_service.batch_upsert(db, payload.items), msg="保存成功")


# ─────────────────────────── 单项 ───────────────────────────
@router.get("/{key}", response_model=ResponseModel, summary="配置详情")
async def get_setting(
    key: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
) -> dict:
    return resp.success(await setting_service.get_setting(db, key))


@router.put("/{key}", response_model=ResponseModel, summary="写入单项配置")
async def put_setting(
    key: str,
    payload: SettingValueUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    data = await setting_service.upsert(
        db,
        key,
        value=payload.setting_value,
        setting_type=payload.setting_type,
        description=payload.description,
        is_public=payload.is_public,
    )
    return resp.success(data, msg="保存成功")


@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 新增配置",
)
async def create_setting(
    payload: SettingUpsert,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    data = await setting_service.upsert(
        db,
        payload.setting_key,
        value=payload.setting_value,
        setting_type=payload.setting_type,
        description=payload.description,
        is_public=payload.is_public,
    )
    return resp.success(data, msg="创建成功")


@router.delete("/{key}", response_model=ResponseModel, summary="删除配置")
async def delete_setting(
    key: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    await setting_service.delete_setting(db, key)
    return resp.success(None, msg="已删除")
