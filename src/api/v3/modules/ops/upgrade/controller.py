"""ops.upgrade 模块路由（T5-11 批次 5：在线升级管理）

::

    GET    /api/v3/ops/upgrade/status   升级状态（当前版本 / app_path / 最近 10 条历史）
    POST   /api/v3/ops/upgrade/check    检查更新（远端 GitHub 优先，回退本地 releases）
    POST   /api/v3/ops/upgrade/apply    升级干跑预检（不执行真实替换，人工/二期动作）

权限码：``module_ops:upgrade:view``（status）、``module_ops:upgrade:execute``
（check / apply）。check 为只读语义但按契约走 POST + EXECUTE。
无独立表：版本读自 version.txt，历史读自 logs/update_history.json。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.upgrade.schema import UpgradeApplyPayload
from src.api.v3.modules.ops.upgrade.service import upgrade_service

router = APIRouter(prefix="/upgrade", tags=["ops-upgrade"], route_class=OperationLogRoute)


@router.get("/status", response_model=ResponseModel, summary="升级状态")
async def status(
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_VIEW),
) -> dict:
    return resp.success(await upgrade_service.status())


@router.post("/check", response_model=ResponseModel, summary="检查更新")
async def check(
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_EXECUTE),
) -> dict:
    return resp.success(await upgrade_service.check())


@router.post("/apply", response_model=ResponseModel, summary="升级干跑预检")
async def apply(
    payload: UpgradeApplyPayload,
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_EXECUTE),
) -> dict:
    return resp.success(await upgrade_service.precheck_apply(payload.target_version), msg="预检完成")
