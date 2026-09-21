"""backup 模块业务逻辑（薄封装 ``BackupService`` + 云存储编排）"""

import asyncio
import json
import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.system.backup_service import BackupService
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.secret_box import decrypt_secret, encrypt_secret
from src.api.v3.modules.ops.backup import cloud
from src.api.v3.modules.ops.backup.schema import CloudConfigPayload
from src.api.v3.modules.system.setting.service import setting_service

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
        kind = (backup_type or "database").lower()
        # 增量 / 差异备份不能单独恢复：必须从基准全量开始按链应用
        if kind in ("incremental", "differential"):
            return await self.restore_chain(backup_file)
        kind = self._validate_type(kind)
        if kind == "files":
            result = await self._service.restore_files(backup_file)
        else:
            result = await self._service.restore_database(backup_file)
        if not result.get("success"):
            raise BadRequestError(result.get("error", "恢复失败"))
        return result

    # ------------------------------------------------------------------ 增量 / 差异备份
    async def create_incremental(
        self,
        *,
        base_path: Optional[str] = None,
        tables: Optional[List[str]] = None,
        differential: bool = False,
    ) -> dict:
        """创建增量 / 差异备份（相对基准的**变化表数据快照**，不含结构）"""
        result = await self._service.create_incremental_backup(
            base_path=base_path, tables=tables, differential=differential
        )
        if not result.get("success"):
            raise BadRequestError(result.get("error", "增量备份失败"))
        return result

    async def chain_plan(self, backup_path: str) -> dict:
        """恢复链预览：这个备份要挂在哪些前置备份后面才能还原"""
        chain = await asyncio.to_thread(self._service.build_restore_chain, backup_path)
        if not chain:
            raise BadRequestError(
                f"无法解析恢复链（备份不存在，或它不是挂在某个基准上的增量/差异备份）：{backup_path}"
            )
        return {
            "length": len(chain),
            "items": [
                {
                    "filename": item.get("filename"),
                    "type": item.get("type"),
                    "created_at": item.get("created_at"),
                    "tables": item.get("tables") or [],
                    "size_human": item.get("size_human"),
                }
                for item in chain
            ],
        }

    async def restore_chain(self, backup_path: str, *, truncate: bool = True) -> dict:
        """按恢复链还原：基准全量 → 依次覆盖增量里的表"""
        result = await self._service.restore_backup_chain(backup_path, truncate=truncate)
        if not result.get("success"):
            raise BadRequestError(result.get("error", "链式恢复失败"))
        return result

    # ------------------------------------------------------------------ 校验
    async def verify(self, backup_path: str) -> dict:
        """校验备份完整性（真读文件：sha256 / 归档可读 / pg_restore --list）"""
        return await self._service.verify_backup(backup_path)

    async def delete_backup(self, backup_path: str) -> bool:
        return bool(await asyncio.to_thread(self._service.delete_backup, backup_path))

    async def cleanup(self, days_to_keep: Optional[int] = None) -> dict:
        result = await self._service.cleanup_old_backups(days=days_to_keep)
        return result or {}

    # ------------------------------------------------------------------ 云存储
    async def cloud_config(self, db: AsyncSession) -> dict:
        """读云存储配置（密钥永不回传，只回 ``has_secret``）"""
        return cloud.mask(await self._raw_cloud_config(db))

    async def save_cloud_config(self, db: AsyncSession, payload: CloudConfigPayload) -> dict:
        """保存云存储配置（密钥落库前加密；留空保持原值）"""
        if payload.provider and payload.provider not in cloud.SUPPORTED_CLOUD_PROVIDERS:
            raise BadRequestError(
                f"不支持的云存储提供商：{payload.provider}（可选 {list(cloud.SUPPORTED_CLOUD_PROVIDERS)}）"
            )
        existing = await self._raw_cloud_config(db)
        data = payload.model_dump(mode="json", exclude_unset=True)
        if data.get("secret"):
            data["secret_encrypted"] = encrypt_secret(str(data.pop("secret")))
        else:
            data.pop("secret", None)  # 留空保持原值
        data["updated_at"] = _now_iso()
        merged = {**existing, **data}
        await setting_service.upsert(
            db,
            cloud.CLOUD_SETTING_KEY,
            value=json.dumps(merged, ensure_ascii=False),
            setting_type="json",
            description="备份云存储配置（ops/backup 管理；密钥已加密）",
            is_public=False,
        )
        logger.info("backup 云存储配置已更新：provider=%s", merged.get("provider"))
        return cloud.mask(merged)

    async def upload_to_cloud(self, db: AsyncSession, backup_path: str) -> dict:
        """把某个备份上传到已配置的云存储（**真实调用**；未配置 / 凭据坏掉一律如实报错）"""
        config = await self._raw_cloud_config(db)
        provider = str(config.get("provider") or "").strip()
        if not provider:
            raise BadRequestError("尚未配置云存储提供商（provider），无法上传")
        if provider not in cloud.SUPPORTED_CLOUD_PROVIDERS:
            raise BadRequestError(
                f"不支持的云存储提供商：{provider}（可选 {list(cloud.SUPPORTED_CLOUD_PROVIDERS)}）"
            )

        secret = self._cloud_secret(config)
        resolved = await asyncio.to_thread(self._service.resolve_backup_path, backup_path)
        if not resolved:
            raise BadRequestError(f"备份不存在或不在备份目录内：{backup_path}")

        filename = os.path.basename(resolved)
        key = cloud.build_object_key(str(config.get("prefix") or cloud.DEFAULT_PREFIX), filename)
        result = await cloud.upload_backup(
            provider=provider, config=config, secret=secret, path=resolved, key=key
        )
        await asyncio.to_thread(self._service.record_cloud_upload, resolved, result)
        logger.info("backup 已上传到云端：%s → %s", filename, result.get("location"))
        return result

    async def _raw_cloud_config(self, db: AsyncSession) -> dict:
        try:
            setting = await setting_service.get_setting(db, cloud.CLOUD_SETTING_KEY)
        except Exception:  # noqa: BLE001 - 键不存在即"尚未配置"
            return {}
        value = setting.get("parsed_value") or {}
        return value if isinstance(value, dict) else {}

    def _cloud_secret(self, config: dict) -> str:
        encrypted = str(config.get("secret_encrypted") or "")
        if not encrypted:
            return ""
        try:
            return decrypt_secret(encrypted)
        except ValueError as exc:
            raise BadRequestError(
                "云存储密钥无法解密（SECRET_KEY 变更或数据损坏）；请在配置页重新填写"
            ) from exc


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


backup_ops_service = BackupOpsService()
