"""ops.upgrade 模块路由（T5-11 批次 5：在线升级管理；批次 18 整合真实执行器）

::

    GET    /api/v3/ops/upgrade/status    升级状态（版本 / 进行中 / 最近结果 / 历史）
    POST   /api/v3/ops/upgrade/check     检查更新（远端 GitHub 优先，回退本地 releases）
    POST   /api/v3/ops/upgrade/apply     升级干跑预检（只体检、不替换；保留兼容）
    GET    /api/v3/ops/upgrade/paths     路径策略（会替换哪些代码、绝不动哪些数据）
    POST   /api/v3/ops/upgrade/plan      执行预演（列出将替换/跳过的文件，只读）
    POST   /api/v3/ops/upgrade/execute   **真实升级**（替换代码 + alembic + 清缓存 + 可选重启）
    GET    /api/v3/ops/upgrade/backups   本地升级备份列表
    POST   /api/v3/ops/upgrade/rollback  按备份回滚代码文件
    GET    /api/v3/ops/upgrade/settings  读取升级设置（重启命令）
    PUT    /api/v3/ops/upgrade/settings  保存升级设置（**该命令会被真实执行**）

权限码：``module_ops:upgrade:view``（status / paths / backups / settings 读取）、
``module_ops:upgrade:execute``（check / apply / plan / execute / rollback / settings 写入）。
check 为只读语义但按既有契约走 POST + EXECUTE。

无独立表：版本读 ``version.txt``，历史读 ``logs/update_history.json``，
备份在 ``backups/update_backups/<old_ver>_<ts>/``（含 ``manifest.json``）。
执行器原先在仓库根的 ``updater/``，2026-09-21 批次 18 整合进 ``executor.py`` 并删除原目录。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.upgrade.schema import (
    UpgradeApplyPayload,
    UpgradeExecutePayload,
    UpgradeRollbackPayload,
    UpgradeSettingsPayload,
)
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


@router.get("/paths", response_model=ResponseModel, summary="路径策略（会动什么 / 绝不动什么）")
async def paths(
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_VIEW),
) -> dict:
    """真实升级的边界：允许替换的代码路径 + 永不触碰的数据/凭据路径。"""
    return resp.success(await upgrade_service.path_policy())


@router.post("/plan", response_model=ResponseModel, summary="执行预演（不落盘）")
async def plan(
    payload: UpgradeApplyPayload,
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_EXECUTE),
) -> dict:
    """列出包里**将被替换**与**被跳过**（保护路径 / 不在允许清单）的文件。"""
    return resp.success(await upgrade_service.plan(payload.target_version))


@router.post("/execute", response_model=ResponseModel, summary="真实升级（替换代码）")
async def execute(
    payload: UpgradeExecutePayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_EXECUTE),
    wait: bool = Query(default=False, description="同步等待完成（便于测试小包）；默认后台执行"),
) -> dict:
    """**这是真的升级**：替换白名单内的代码文件、跑 ``alembic upgrade head``、
    清 ``storage/cache``、按配置可选重启；失败自动回滚。必须显式 ``confirm=true``。
    """
    data = await upgrade_service.execute(db, payload, wait=wait)
    msg = "升级完成" if data.get("ok") else ("升级已开始" if data.get("started") else "升级失败")
    return resp.success(data, msg=msg)


@router.get("/backups", response_model=ResponseModel, summary="升级备份列表")
async def backups(
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_VIEW),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    return resp.success(await upgrade_service.list_backups(limit))


@router.post("/rollback", response_model=ResponseModel, summary="按备份回滚代码")
async def rollback(
    payload: UpgradeRollbackPayload,
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_EXECUTE),
) -> dict:
    """按 ``manifest.json`` 精确还原被替换的文件（新增文件会被删掉）。需 ``confirm=true``。"""
    return resp.success(await upgrade_service.rollback(payload), msg="已回滚")


@router.get("/settings", response_model=ResponseModel, summary="读取升级设置")
async def get_settings(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_VIEW),
) -> dict:
    return resp.success(await upgrade_service.get_settings(db))


@router.put("/settings", response_model=ResponseModel, summary="保存升级设置（重启命令）")
async def save_settings(
    payload: UpgradeSettingsPayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.UPGRADE_EXECUTE),
) -> dict:
    """设置升级后执行的重启命令（**会被服务端真实执行**，如 ``docker compose restart backend``）；
    留空表示不自动重启，升级完成后提示人工重启。"""
    return resp.success(await upgrade_service.save_settings(db, payload), msg="已保存")
