"""backup 模块业务逻辑（薄封装 ``BackupService``）"""

import asyncio
from typing import List, Optional

from shared.services.system.backup_service import BackupService
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger

logger = get_logger("backup")

VALID_BACKUP_TYPES = {"full", "database", "files"}


class BackupOpsService:
    """备份管理"""

    def __init__(self) -> None:
        self._service = BackupService()

    # ------------------------------------------------------------------ 创建
    def _validate_type(self, backup_type: str) -> str:
        kind = (backup_type or "full").lower()
        if kind not in VALID_BACKUP_TYPES:
            raise BadRequestError(f"不支持的备份类型: {kind}")
        return kind

    async def create_database_backup(self, backup_type: str = "full") -> dict:
        kind = self._validate_type(backup_type)
        result = await self._service.backup_database(backup_type=kind)
        if not result.get("success"):
            raise BadRequestError(result.get("error", "数据库备份失败"))
        return result

    async def create_files_backup(self) -> dict:
        result = await self._service.backup_files()
        if not result.get("success"):
            raise BadRequestError(result.get("error", "文件备份失败"))
        return result

    async def create_full_backup(self) -> dict:
        result = await self._service.full_backup()
        if not result.get("success"):
            raise BadRequestError(result.get("error", "全量备份失败"))
        return result

    # ------------------------------------------------------------------ 查询
    async def list_backups(
        self, *, backup_type: Optional[str] = None, limit: Optional[int] = None
    ) -> List[dict]:
        items = await asyncio.to_thread(
            self._service.list_backups, backup_type, limit
        )
        return list(items or [])

    async def stats(self) -> dict:
        return await asyncio.to_thread(self._service.get_backup_stats)

    async def schedule(self) -> dict:
        return await asyncio.to_thread(self._service.get_backup_schedule)

    async def update_schedule(self, config: dict) -> dict:
        await asyncio.to_thread(self._service.update_backup_schedule, config)
        return await self.schedule()

    # ------------------------------------------------------------------ 恢复 / 删除
    async def restore(self, backup_file: str, backup_type: str = "database") -> dict:
        kind = self._validate_type(backup_type)
        if kind == "files":
            result = await self._service.restore_files(backup_file)
        else:
            result = await self._service.restore_database(backup_file)
        if not result.get("success"):
            raise BadRequestError(result.get("error", "恢复失败"))
        return result

    async def delete_backup(self, backup_path: str) -> bool:
        return bool(await asyncio.to_thread(self._service.delete_backup, backup_path))

    async def cleanup(self, days_to_keep: Optional[int] = None) -> dict:
        result = await self._service.cleanup_old_backups(days=days_to_keep)
        return result or {}


backup_ops_service = BackupOpsService()
