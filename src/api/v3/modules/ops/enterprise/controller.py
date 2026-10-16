"""enterprise 模块路由（ops 域：企业版授权）

::

    GET    /api/v3/ops/enterprise/license                       许可证列表
    POST   /api/v3/ops/enterprise/license                       新建许可证
    PUT    /api/v3/ops/enterprise/license/{license_id}          更新许可证
    DELETE /api/v3/ops/enterprise/license/{license_id}          删除许可证
    GET    /api/v3/ops/enterprise/retention-policy              保留策略列表
    POST   /api/v3/ops/enterprise/retention-policy              新建保留策略
    PUT    /api/v3/ops/enterprise/retention-policy/{policy_id}  更新保留策略
    DELETE /api/v3/ops/enterprise/retention-policy/{policy_id}  删除保留策略

权限码：``module_ops:enterprise:view``（读）/ ``module_ops:enterprise:edit``（写）。
license_key 唯一（重复 → 409）；features 入参列表、落库 JSON、出参还原列表。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.enterprise.schema import (
    DataRetentionPolicyCreate,
    DataRetentionPolicyUpdate,
    EnterpriseLicenseCreate,
    EnterpriseLicenseUpdate,
)
from src.api.v3.modules.ops.enterprise.service import (
    data_retention_policy_service,
    enterprise_license_service,
)

router = APIRouter(prefix="/enterprise", tags=["ops-enterprise"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 企业许可证
@router.get("/license", response_model=ResponseModel, summary="企业许可证列表")
async def list_licenses(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ENTERPRISE_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await enterprise_license_service.list_licenses(
        db, page=page, page_size=page_size, keyword=keyword
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/license", response_model=ResponseModel, summary="新建企业许可证")
async def create_license(
    payload: EnterpriseLicenseCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ENTERPRISE_EDIT),
) -> dict:
    return resp.success(await enterprise_license_service.create_license(db, payload), msg="已创建")


@router.put("/license/{license_id}", response_model=ResponseModel, summary="更新企业许可证")
async def update_license(
    license_id: int,
    payload: EnterpriseLicenseUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ENTERPRISE_EDIT),
) -> dict:
    return resp.success(
        await enterprise_license_service.update_license(db, license_id, payload), msg="已保存"
    )


@router.delete("/license/{license_id}", response_model=ResponseModel, summary="删除企业许可证")
async def delete_license(
    license_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ENTERPRISE_EDIT),
) -> dict:
    await enterprise_license_service.delete_license(db, license_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 数据保留策略
@router.get("/retention-policy", response_model=ResponseModel, summary="数据保留策略列表")
async def list_policies(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ENTERPRISE_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await data_retention_policy_service.list_policies(
        db, page=page, page_size=page_size, keyword=keyword
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/retention-policy", response_model=ResponseModel, summary="新建数据保留策略")
async def create_policy(
    payload: DataRetentionPolicyCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ENTERPRISE_EDIT),
) -> dict:
    return resp.success(
        await data_retention_policy_service.create_policy(db, payload), msg="已创建"
    )


@router.put(
    "/retention-policy/{policy_id}", response_model=ResponseModel, summary="更新数据保留策略"
)
async def update_policy(
    policy_id: int,
    payload: DataRetentionPolicyUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ENTERPRISE_EDIT),
) -> dict:
    return resp.success(
        await data_retention_policy_service.update_policy(db, policy_id, payload), msg="已保存"
    )


@router.delete(
    "/retention-policy/{policy_id}", response_model=ResponseModel, summary="删除数据保留策略"
)
async def delete_policy(
    policy_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ENTERPRISE_EDIT),
) -> dict:
    await data_retention_policy_service.delete_policy(db, policy_id)
    return resp.success(None, msg="已删除")
