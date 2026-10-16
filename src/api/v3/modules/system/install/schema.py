"""install 模块的响应模型

只暴露**布尔位与版本号**：不回传连接串、主机名、文件系统路径等细节
（该端点是公开的 —— 未安装的站点还没有管理员可用来鉴权）。
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class DatabaseCheck(SchemaBase):
    ok: bool = False
    #: 只给异常**类型名**，不给完整错误信息（后者可能含连接串/主机）
    error: Optional[str] = Field(default=None, description="失败时的异常类型名")


class MigrationCheck(SchemaBase):
    #: 数据库里 ``alembic_version`` 的当前值
    current: Optional[str] = None
    #: 代码里 alembic 脚本目录的 head
    head: Optional[str] = None
    up_to_date: bool = False


class InstallStatusPayload(SchemaBase):
    """安装状态自检结果"""

    database: DatabaseCheck
    migration: MigrationCheck
    #: 是否存在超级管理员（这就是本项目的"已安装"判定）
    has_superuser: bool = False
    installed: bool = False
    #: CRDT / 实时协同依赖是否可用（缺失时协同编辑不可用，其余功能不受影响）
    realtime_available: bool = False


# ── Web 安装向导（仅 DEPLOYMENT_MODE=single 且尚未安装时可用） ──────────────


class WizardStep(SchemaBase):
    key: str
    label: str
    description: str = ""


class WizardStatusPayload(SchemaBase):
    """向导状态。前端据此决定显示向导还是"请用命令行初始化"。"""

    #: single / enterprise
    deployment_mode: str = "enterprise"
    #: 该部署模式是否开放 Web 向导
    wizard_enabled: bool = False
    installed: bool = False
    #: 现在能否使用向导（= wizard_enabled 且未安装）
    available: bool = False
    steps: List[WizardStep] = Field(default_factory=list)


class WizardDatabaseRequest(SchemaBase):
    """数据库连接配置

    **只入不出**：这个结构只作为请求体，回包一律用 ``WizardStepResult``
    （只给 success/message），绝不回显连接串或密码。
    """

    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(default="", max_length=255)


class WizardAdminRequest(SchemaBase):
    username: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class WizardSettingsRequest(SchemaBase):
    site_name: str = Field(min_length=1, max_length=128)
    site_url: str = Field(default="", max_length=255)
    site_description: str = Field(default="", max_length=500)


class WizardStepResult(SchemaBase):
    """向导任一步骤的结果

    只回 ``success`` / ``message`` / 少量布尔位 —— 与 ``status`` 同一口径：
    不回传连接串、主机名、文件系统路径（该模块端点公开可读）。
    """

    success: bool = False
    message: str = ""
    #: 该步产生的可选细节（如环境检测的逐项结果），键值均为非敏感项
    detail: Optional[Dict[str, Any]] = None
