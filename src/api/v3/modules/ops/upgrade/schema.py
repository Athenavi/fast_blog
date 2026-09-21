"""upgrade 模块的请求 / 响应模型（在线升级管理，无独立表）

data 内字段名与前端契约对齐，不得随意变更：

- ``UpgradeStatusOut``  → GET /status
- ``UpgradeCheckOut``   → POST /check
- ``UpgradeApplyOut``   → POST /apply（干跑预检）
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: check.source 的取值域（与前端契约一致）
CHECK_SOURCES = ("remote", "local_releases", "none")


class UpgradeApplyPayload(SchemaBase):
    """POST /apply 请求体：干跑预检的目标版本（来自 /check 的 latest_version）"""

    target_version: str = Field(
        min_length=1,
        max_length=64,
        description="目标版本号，例如 0.7.27.0910",
    )


class UpgradeHistoryItem(SchemaBase):
    """升级历史单条（源自 update_history 的记录，started_at 由 timestamp-duration 反推）"""

    target_version: str
    status: str
    started_at: str
    finished_at: str
    message: Optional[str] = None


class UpgradeStatusOut(SchemaBase):
    """GET /status 响应体"""

    current_version: str = ""
    app_path: str = ""
    in_progress: bool = False
    #: 正在执行的目标版本（in_progress=True 时有值）
    in_progress_target: Optional[str] = None
    #: 最近一次执行/回滚的结果（进程内保留；多 worker 下只反映本 worker）
    last_result: Optional[dict] = None
    history: list[UpgradeHistoryItem] = Field(default_factory=list)


class UpgradeCheckOut(SchemaBase):
    """POST /check 响应体（远端不可达时结构化返回，不抛异常）"""

    current_version: str
    latest_version: Optional[str] = None
    has_update: bool = False
    source: str = "none"
    detail: str = ""


class UpgradeCheckItem(SchemaBase):
    """干跑预检单项"""

    name: str
    passed: bool
    detail: str = ""


class UpgradeApplyOut(SchemaBase):
    """POST /apply 响应体（本期固定 dry_run=True，真实替换为人工/二期动作）"""

    dry_run: bool = True
    ready: bool = False
    checks: list[UpgradeCheckItem] = Field(default_factory=list)


class UpgradeStepOut(SchemaBase):
    """真实执行的单步结果"""

    step: str
    ok: bool
    detail: str = ""


class UpgradeExecutePayload(SchemaBase):
    """POST /execute 请求体：**真实升级**（改文件、跑迁移、可选重启）"""

    target_version: str = Field(min_length=1, max_length=64)
    confirm: bool = Field(
        default=False,
        description="必须显式传 true 才会真正执行（防止误触；替换是写文件操作）",
    )
    run_migration: bool = Field(default=True, description="替换后执行 alembic upgrade head")
    clear_cache: bool = Field(default=True, description="替换后清理 storage/cache")


class UpgradeExecuteOut(SchemaBase):
    """真实执行 / 回滚的结果"""

    dry_run: bool = False
    ok: bool = False
    from_version: str = ""
    target_version: str = ""
    backup_id: Optional[str] = None
    files_replaced: int = 0
    skipped: int = 0
    need_restart: bool = True
    restart_detail: Optional[str] = None
    steps: list[UpgradeStepOut] = Field(default_factory=list)


class UpgradePlanOut(SchemaBase):
    """执行预演：包里哪些文件会被替换、哪些被跳过"""

    target_version: str
    package: str = ""
    package_detail: str = ""
    will_replace_count: int = 0
    skipped_count: int = 0
    will_replace: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    collisions_with_protected: list[str] = Field(default_factory=list)


class UpgradeBackupItem(SchemaBase):
    """本地升级备份"""

    backup_id: str
    from_version: Optional[str] = None
    target_version: Optional[str] = None
    created_at: Optional[str] = None
    files: int = 0
    path: str = ""


class UpgradeRollbackPayload(SchemaBase):
    """POST /rollback 请求体"""

    backup_id: str = Field(min_length=1, max_length=128)
    confirm: bool = False


class UpgradeSettingsPayload(SchemaBase):
    """PUT /settings 请求体：升级后重启命令（真实执行的 shell 命令）"""

    restart_command: Optional[str] = Field(
        default=None,
        max_length=500,
        description="替换成功后执行的重启命令（如 docker compose restart backend）；留空表示不自动重启",
    )


class UpgradeSettingsOut(SchemaBase):
    """GET /settings 响应体"""

    restart_command: Optional[str] = None
    configured: bool = False
