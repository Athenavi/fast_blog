"""supervisor 模块的请求 / 响应模型（进程登记 + 状态 + 动作结果）

登记项存在 ``system_settings`` 的 ``supervisor.config``（JSON），**无独立表**（用户拍板）。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: 进程名字符集（与后端 admin_menus.code 风格一致，便于前端路由与日志定位）
NAME_PATTERN = r"^[A-Za-z0-9._-]+$"


class SupervisorHealthConfig(SchemaBase):
    """三层健康检查配置（未配置的层跳过并如实说明）"""

    host: str = Field(default="127.0.0.1", max_length=100)
    port: Optional[int] = Field(default=None, ge=1, le=65535, description="端口监听检查")
    url: Optional[str] = Field(default=None, max_length=500, description="HTTP 端点检查")


class SupervisorProcessPayload(SchemaBase):
    """一个被托管的进程登记项"""

    name: str = Field(min_length=1, max_length=100, pattern=NAME_PATTERN)
    description: Optional[str] = Field(default=None, max_length=200)
    start_command: Optional[str] = Field(default=None, max_length=500)
    stop_command: Optional[str] = Field(default=None, max_length=500)
    restart_command: Optional[str] = Field(default=None, max_length=500)
    pid_file: Optional[str] = Field(default=None, max_length=255, description="可选：读 pid 采指标")
    log_file: Optional[str] = Field(default=None, max_length=255, description="必须在 logs/ 内")
    health: SupervisorHealthConfig = Field(default_factory=SupervisorHealthConfig)
    is_active: bool = True


class SupervisorConfigPayload(SchemaBase):
    """PUT /config：整体替换登记（与 system_settings 的 JSON 存储一致）"""

    processes: list[SupervisorProcessPayload] = Field(default_factory=list)


class SupervisorProcessOut(SupervisorProcessPayload):
    """登记项 + 实时探测结果（列表用）"""

    probe: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)


class SupervisorConfigOut(SchemaBase):
    """GET /config、PUT /config 响应体"""

    processes: list[SupervisorProcessOut] = Field(default_factory=list)
    total: int = 0
    updated_at: Optional[str] = None
    #: 保存时被拒绝的项（校验失败原因），保存成功时为空
    issues: list[str] = Field(default_factory=list)


class SupervisorActionPayload(SchemaBase):
    """启停 / 重启请求体"""

    confirm: bool = Field(default=False, description="必须显式传 true（会真实执行部署命令）")


class SupervisorActionOut(SchemaBase):
    """动作结果（失败时 detail 写明原因，绝不静默）"""

    ok: bool = False
    action: str = ""
    process: str = ""
    command: Optional[str] = None
    returncode: Optional[int] = None
    duration_ms: Optional[int] = None
    detail: str = ""
    output: Optional[str] = None


class SupervisorLogOut(SchemaBase):
    """日志读取结果"""

    available: bool = False
    detail: Optional[str] = None
    path: Optional[str] = None
    total_lines: int = 0
    lines: list[str] = Field(default_factory=list)


class SupervisorHealthOut(SchemaBase):
    """三层健康检查结果"""

    process: str = ""
    healthy: bool = False
    alive: Optional[bool] = None
    port_open: Optional[bool] = None
    http_ok: Optional[bool] = None
    detail: list[str] = Field(default_factory=list)
