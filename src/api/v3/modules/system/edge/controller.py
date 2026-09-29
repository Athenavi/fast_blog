"""edge 模块路由：边缘函数（Cloudflare Workers / Vercel Edge）

::

    GET    /api/v3/system/edge/function                     函数列表（可选 ?path= 预览路由命中）
    POST   /api/v3/system/edge/function                     注册函数
    GET    /api/v3/system/edge/function/{name}              函数详情（含源码）
    DELETE /api/v3/system/edge/function/{name}              删除函数
    POST   /api/v3/system/edge/function/{name}/validate     代码校验 + 产物摘要
    POST   /api/v3/system/edge/function/{name}/deploy       部署（无凭据时如实返回未部署）
    GET    /api/v3/system/edge/function/{name}/log          操作/部署日志（本地记录）

权限码：``module_system:integration:view/create/edit/delete``（第三方集成）。

**安全**：校验 / 部署只做静态检查，**从不执行**用户提交的代码。
"""

from typing import Optional

from fastapi import APIRouter, Body, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.edge.schema import (
    EdgeFunctionCreate,
    EdgeFunctionValidateRequest,
)
from src.api.v3.modules.system.edge.service import edge_function_service

router = APIRouter(prefix="/edge", tags=["system-edge"], route_class=OperationLogRoute)


@router.get("/function", response_model=ResponseModel, summary="边缘函数列表")
async def list_functions(
    db: DBSession,
    _current: CurrentUser,
    path: Optional[str] = Query(default=None, description="按此路径预览命中的函数"),
    _perm=AuthControl(codes.INTEGRATION_VIEW),
) -> dict:
    return resp.success(await edge_function_service.list_functions(db, path=path))


@router.post("/function", response_model=ResponseModel, summary="注册边缘函数")
async def create_function(
    payload: EdgeFunctionCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_CREATE),
) -> dict:
    """落到 ``system_settings`` 的 ``edge.functions``（JSON 对象，键=函数名）"""
    return resp.success(
        await edge_function_service.create_function(
            db, payload, user_id=getattr(current, "id", None)
        ),
        msg="已注册",
    )


@router.get("/function/{name}", response_model=ResponseModel, summary="边缘函数详情")
async def get_function(
    name: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_VIEW),
) -> dict:
    return resp.success(await edge_function_service.get_function(db, name))


@router.delete("/function/{name}", response_model=ResponseModel, summary="删除边缘函数")
async def delete_function(
    name: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_DELETE),
) -> dict:
    await edge_function_service.delete_function(db, name)
    return resp.success(None, msg="已删除")


@router.post("/function/{name}/validate", response_model=ResponseModel, summary="校验边缘函数代码")
async def validate_function(
    name: str,
    db: DBSession,
    _current: CurrentUser,
    payload: Optional[EdgeFunctionValidateRequest] = Body(
        default=None, description="可选：临时校验尚未保存的代码（编辑器场景）"
    ),
    _perm=AuthControl(codes.INTEGRATION_EDIT),
) -> dict:
    """平台特定的静态校验（体积 / 禁用 API / 入口契约）+ 将部署的产物摘要"""
    return resp.success(
        await edge_function_service.validate_function(
            db, name, override_code=payload.code if payload else None
        )
    )


@router.post("/function/{name}/deploy", response_model=ResponseModel, summary="部署边缘函数")
async def deploy_function(
    name: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.INTEGRATION_EDIT),
) -> dict:
    """无平台凭据时**如实**返回 ``{"deployed": false, "reason": "未配置平台凭据"}``（不伪造）"""
    return resp.success(await edge_function_service.deploy_function(db, name))


@router.get("/function/{name}/log", response_model=ResponseModel, summary="边缘函数日志")
async def log_function(
    name: str,
    db: DBSession,
    _current: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200, description="返回最近 N 条"),
    _perm=AuthControl(codes.INTEGRATION_VIEW),
) -> dict:
    return resp.success(await edge_function_service.log_function(db, name, limit=limit))
