"""install 模块路由（系统安装自检 + 单机模式 Web 安装向导）

**公开读（无鉴权）**::

    GET  /api/v3/system/install/status    安装状态自检
    GET  /api/v3/system/install/wizard    向导状态（部署模式 / 是否开放 / 步骤定义）

**Web 安装向导写口（仅 ``DEPLOYMENT_MODE=single`` 且尚未安装）**::

    POST /api/v3/system/install/wizard/prerequisites   环境检测
    POST /api/v3/system/install/wizard/database        配置数据库并测试连接
    POST /api/v3/system/install/wizard/migrate         执行数据库迁移
    POST /api/v3/system/install/wizard/admin           创建管理员
    POST /api/v3/system/install/wizard/settings        站点设置
    POST /api/v3/system/install/wizard/complete        完成安装（锁定）

## 为什么写口按部署模式分流

原实现**只有只读 status**（用户拍板）：未安装的站点没有管理员可用于鉴权，
开放写口等于"任何人可重建超管"。但单机 / 极客用户确实需要 Web 向导，
而他们通常是本地或内网部署。于是按部署模式分开对待：

  - ``enterprise``（**默认**）：保持只读 + 命令行初始化，风险面为零；
  - ``single``：开放向导，且**仅在尚未安装时** —— 安装完成即永久关闭。

两道闸门由 ``_require_wizard`` 强制，任一不满足即 403。这样企业部署依然满足
原注释里"不存在任何人重建超管的风险面"的承诺。

## 闸门为什么是 dependency 而不是函数体内的检查

FastAPI 的**请求体校验发生在处理函数之前**。若把判定写在函数体里，带必填 body
的端点（database / admin / settings）在未授权时会先返回 422（body 不合法）而不是
403（该部署不开放）—— 语义不准，且把校验细节暴露给了不该到达这一步的请求。
做成 ``dependencies=[Depends(...)]`` 即可先于 body 校验生效。

权限码：无 —— 未安装时不存在任何可用于鉴权的账号，因此向导写口由
**部署模式 + 安装状态**把关，而不是权限码。
"""

import os
from typing import Any

from fastapi import APIRouter, Depends

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.exceptions import ForbiddenError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.install.schema import (
    WizardAdminRequest,
    WizardDatabaseRequest,
    WizardSettingsRequest,
)
from src.api.v3.modules.system.install.service import install_service, wizard_enabled

router = APIRouter(prefix="/install", tags=["system-install"])

logger = get_logger("system.install")


@router.get("/status", response_model=ResponseModel, summary="安装状态自检")
async def install_status() -> dict:
    """数据库连通性 / 迁移是否就位 / 是否已有超管 / 实时协同依赖是否可用

    **已安装 + 生产环境时只回 ``{"installed": true}``**：迁移版本、数据库错误类型、
    超管存在性都属于未授权侦察面（攻击者可据此推断已知漏洞与账号情况），
    而安装完成后运维已有别的渠道查看这些信息。
    """
    data = await install_service.status()

    if data.get("installed") and os.environ.get("ENVIRONMENT", "").lower() == "production":
        return resp.success({"installed": True})
    return resp.success(data)


# ─────────────────────────── Web 安装向导（单机模式）───────────────────────────


def _wizard() -> Any:
    """惰性取向导服务实例

    不在模块顶层 import：``InstallationWizardService`` 会解析项目根路径并触碰
    ``storage/``，而企业化部署下这些端点根本用不到，没必要在每次导入路由时都执行。
    """
    from shared.services.install.install_manager.install_wizard import (
        installation_wizard_service,
    )

    return installation_wizard_service


def _require_wizard() -> None:
    """向导写口的准入闸门 —— 两道闸门，缺一不可（作为 dependency 生效）

    1. **部署模式必须是 ``single``**：企业化部署（默认）不开放 Web 写口，
       保持"只读 + 命令行初始化"的原决策；
    2. **必须尚未安装**：安装完成即永久关闭，不给"重建超管"留窗口。
    """
    if not wizard_enabled():
        raise ForbiddenError(
            "当前部署模式不开放 Web 安装向导（企业化部署请用命令行初始化）"
        )
    if _wizard().is_installed():
        raise ForbiddenError("站点已安装，安装向导已永久关闭")


#: 所有写口共用 —— 见模块注释里"闸门为什么是 dependency"
_WIZARD_ONLY = [Depends(_require_wizard)]


@router.get("/wizard", response_model=ResponseModel, summary="Web 安装向导状态")
async def wizard_status() -> dict:
    """部署模式 / 是否开放 / 是否可安装 / 步骤定义

    前端据此决定显示向导还是"请用命令行初始化"，不需要自己猜部署模式。
    只读，不含任何敏感项，因此不需要过闸门。
    """
    return resp.success(install_service.wizard_status())


@router.post(
    "/wizard/prerequisites",
    response_model=ResponseModel,
    summary="[向导] 环境检测",
    dependencies=_WIZARD_ONLY,
)
async def wizard_prerequisites() -> dict:
    return resp.success(_wizard().check_prerequisites())


@router.post(
    "/wizard/database",
    response_model=ResponseModel,
    summary="[向导] 配置数据库连接",
    dependencies=_WIZARD_ONLY,
)
async def wizard_database(payload: WizardDatabaseRequest) -> dict:
    """先测连接，通了才写 ``.env``

    顺序很重要：直接写配置会把站点留在"配了但连不上"的状态，之后每次启动都失败，
    而部署者以为是别的问题。
    """
    config = {
        "host": payload.host,
        "port": str(payload.port),
        "database": payload.database,
        "username": payload.username,
        "password": payload.password,
    }
    check = _wizard().check_database_connection(config)
    if not check.get("success"):
        return resp.success(
            {"success": False, "message": check.get("message") or "数据库连接失败"}
        )
    return resp.success(_wizard().configure_database(config))


@router.post(
    "/wizard/migrate",
    response_model=ResponseModel,
    summary="[向导] 执行数据库迁移",
    dependencies=_WIZARD_ONLY,
)
async def wizard_migrate() -> dict:
    return resp.success(_wizard().confirm_database_and_migrate())


@router.post(
    "/wizard/admin",
    response_model=ResponseModel,
    summary="[向导] 创建管理员账号",
    dependencies=_WIZARD_ONLY,
)
async def wizard_admin(payload: WizardAdminRequest) -> dict:
    try:
        return resp.success(
            _wizard().create_admin_user(payload.username, payload.email, payload.password)
        )
    except Exception as exc:  # noqa: BLE001 - 建号失败要给部署者可读的原因
        logger.warning("安装向导：创建管理员失败（%s）", type(exc).__name__)
        # 只回异常类型名，不回完整信息（可能含连接串）
        return resp.success(
            {"success": False, "message": f"创建管理员失败：{type(exc).__name__}"}
        )


@router.post(
    "/wizard/settings",
    response_model=ResponseModel,
    summary="[向导] 站点设置",
    dependencies=_WIZARD_ONLY,
)
async def wizard_settings(payload: WizardSettingsRequest) -> dict:
    return resp.success(
        _wizard().configure_site_settings(
            {
                "site_name": payload.site_name,
                "site_url": payload.site_url,
                "site_description": payload.site_description,
            }
        )
    )


@router.post(
    "/wizard/complete",
    response_model=ResponseModel,
    summary="[向导] 完成安装",
    dependencies=_WIZARD_ONLY,
)
async def wizard_complete() -> dict:
    """种子 RBAC 并写入安装标记 —— 之后向导写口永久关闭"""
    return resp.success(_wizard().complete_installation({}))
