"""install 模块路由（系统安装自检）

::

    GET /api/v3/system/install/status    安装状态自检（**公开**，只读）

**公开的原因**：未安装的站点根本没有管理员可用于鉴权，此时部署者必须能匿名自查。
作为交换，本模块**只读**：没有任何 setup / initialize 写口（用户拍板），
初始化一律走命令行脚本 —— 因此不存在"任何人重建超管"的风险面。

权限码：无（公开读，不涉及写操作，故也不需要登记写豁免）。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.modules.system.install.service import install_service

router = APIRouter(prefix="/install", tags=["system-install"])


@router.get("/status", response_model=ResponseModel, summary="安装状态自检")
async def install_status() -> dict:
    """数据库连通性 / 迁移是否就位 / 是否已有超管 / 实时协同依赖是否可用

    **已安装 + 生产环境时只回 ``{"installed": true}``**：迁移版本、数据库错误类型、
    超管存在性都属于未授权侦察面（攻击者可据此推断已知漏洞与账号情况），
    而安装完成后运维已有别的渠道查看这些信息。
    """
    data = await install_service.status()
    import os

    if data.get("installed") and os.environ.get("ENVIRONMENT", "").lower() == "production":
        return resp.success({"installed": True})
    return resp.success(data)
