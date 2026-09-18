"""backup 模块的请求 / 响应模型"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class BackupItem(SchemaBase):
    """备份条目元信息（字段随 BackupService 的 metadata 变化，保持宽松）"""

    filename: Optional[str] = None
    path: Optional[str] = None
    type: Optional[str] = None
    backup_type: Optional[str] = None
    size: Optional[int] = None
    size_human: Optional[str] = None
    created_at: Optional[str] = None
    status: Optional[str] = None
    database: Optional[str] = None
    model_config = {"extra": "allow"}


class BackupListOut(SchemaBase):
    items: List[BackupItem] = Field(default_factory=list)
    total: int = 0


class RestoreRequest(SchemaBase):
    backup_file: str = Field(description="备份文件路径或文件名")
    backup_type: str = Field(default="database", description="database / files")


class ScheduleOut(SchemaBase):
    enabled: bool = False
    schedule: Optional[str] = None
    retention_days: Optional[int] = None
    compress: Optional[bool] = None
    backup_database: Optional[bool] = None
    backup_files: Optional[bool] = None


class ScheduleUpdate(SchemaBase):
    auto_backup_enabled: Optional[bool] = None
    auto_backup_schedule: Optional[str] = None
    retention_days: Optional[int] = None
    compress_backups: Optional[bool] = None
    backup_database: Optional[bool] = None
    backup_files: Optional[bool] = None


class StatsOut(SchemaBase):
    total_backups: int = 0
    total_size: int = 0
    total_size_human: Optional[str] = None
    latest_backup: Optional[Any] = None
    by_type: Dict[str, Any] = Field(default_factory=dict)
