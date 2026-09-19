"""email 模块路由（T5-11 批次 2：自 astro `admin/email-templates` 能力域新建）

::

    GET    /api/v3/ops/email/config                配置列表（凭据脱敏）
    POST   /api/v3/ops/email/config                新建配置
    PUT    /api/v3/ops/email/config/{config_id}    更新配置
    DELETE /api/v3/ops/email/config/{config_id}    删除配置
    GET    /api/v3/ops/email/subscription          订阅列表

权限码：``module_ops:email:view/edit/delete``。
真实"邮件模板"需新表（email_templates），二期落地；发送链路复用既有
``shared/services/notifications/email_service_integration.py``。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.email.schema import EmailConfigCreate, EmailConfigUpdate
from src.api.v3.modules.ops.email.service import email_service

router = APIRouter(prefix="/email", tags=["ops-email"], route_class=OperationLogRoute)


@router.get("/config", response_model=ResponseModel, summary="配置列表（凭据脱敏）")
async def list_configs(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.EMAIL_VIEW),
) -> dict:
    return resp.success(await email_service.list_configs(db))


@router.post("/config", response_model=ResponseModel, summary="新建配置")
async def create_config(
    payload: EmailConfigCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.EMAIL_EDIT),
) -> dict:
    return resp.success(await email_service.create_config(db, payload), msg="已创建")


@router.put("/config/{config_id}", response_model=ResponseModel, summary="更新配置")
async def update_config(
    config_id: int,
    payload: EmailConfigUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.EMAIL_EDIT),
) -> dict:
    return resp.success(await email_service.update_config(db, config_id, payload), msg="已保存")


@router.delete("/config/{config_id}", response_model=ResponseModel, summary="删除配置")
async def delete_config(
    config_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.EMAIL_DELETE),
) -> dict:
    await email_service.delete_config(db, config_id)
    return resp.success(None, msg="已删除")


@router.get("/subscription", response_model=ResponseModel, summary="订阅列表")
async def list_subscriptions(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.EMAIL_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await email_service.list_subscriptions(db, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)
