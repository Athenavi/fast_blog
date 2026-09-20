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
