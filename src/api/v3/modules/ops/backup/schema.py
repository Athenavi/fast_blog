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


class BackupPathRequest(SchemaBase):
    """按路径操作某个备份（路径来自列表的 ``path`` / ``filename``）"""

    backup_path: str = Field(description="备份文件路径或文件名")


class IncrementalRequest(SchemaBase):
    """创建增量 / 差异备份"""

    base_path: Optional[str] = Field(
        default=None,
        description="基准备份；缺省取最近一次记录了表指纹的数据库全量备份",
    )
    tables: Optional[List[str]] = Field(
        default=None, description="只检查这些表（缺省为 public 下全部基础表）"
    )
    differential: bool = Field(
        default=False, description="true=差异备份（固定挂最近全量），false=增量备份"
    )


class RestoreChainRequest(SchemaBase):
    backup_path: str = Field(description="链上任意一个备份（会从基准开始依次还原）")
    truncate: bool = Field(
        default=True,
        description="覆盖前先清空这些表；false 会变成追加（可能产生重复行），仅在已知目标表为空时使用",
    )


class VerifyOut(SchemaBase):
    """备份校验结果（``checks`` 逐项列出检查与原因）"""

    valid: bool = False
    path: Optional[str] = None
    kind: Optional[str] = None
    size: Optional[int] = None
    size_human: Optional[str] = None
    checksum: Optional[Dict[str, Any]] = None
    checks: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class RestoreChainPlanOut(SchemaBase):
    """恢复链预览"""

    length: int = 0
    items: List[Dict[str, Any]] = Field(default_factory=list)


class CloudConfigPayload(SchemaBase):
    """云存储配置（密钥只写不读；留空保持原值）"""

    provider: Optional[str] = Field(default=None, description="s3 / oss")
    bucket: Optional[str] = Field(default=None, max_length=255)
    region: Optional[str] = Field(
        default=None, max_length=100, description="S3 默认 us-east-1 / OSS 默认 oss-cn-hangzhou"
    )
    endpoint: Optional[str] = Field(
        default=None, max_length=500, description="自定义端点（私有云 / MinIO / 内网）"
    )
    prefix: Optional[str] = Field(default=None, max_length=255, description="object key 前缀，默认 backups")
    access_key_id: Optional[str] = Field(default=None, max_length=255)
    secret: Optional[str] = Field(
        default=None, description="密钥（入参）；落库前 AES-256-GCM 加密，留空保持原值"
    )


class CloudConfigOut(SchemaBase):
    provider: Optional[str] = None
    bucket: Optional[str] = None
    region: Optional[str] = None
    endpoint: Optional[str] = None
    prefix: Optional[str] = None
    access_key_id: Optional[str] = None
    has_secret: bool = False
    updated_at: Optional[str] = None
    model_config = {"extra": "allow"}


class CloudUploadRequest(SchemaBase):
    backup_path: str = Field(description="要上传的备份（路径或文件名）")


class CloudUploadOut(SchemaBase):
    """上传结果（云端位置）"""

    provider: str = ""
    bucket: Optional[str] = None
    key: Optional[str] = None
    size: Optional[int] = None
    endpoint: Optional[str] = None
    location: Optional[str] = None
    status_code: Optional[int] = None
    model_config = {"extra": "allow"}
