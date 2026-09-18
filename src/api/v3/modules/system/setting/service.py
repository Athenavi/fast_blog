"""setting 模块业务逻辑

``system_settings.setting_value`` 是字符串列，``setting_type`` 描述其真实类型；
本模块负责写入时的归一化与读取时的解析，避免各调用方各自实现一遍。
"""

import json
from typing import Any, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.system import SystemSettings
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.setting.crud import setting_crud
from src.api.v3.modules.system.setting.schema import SettingUpsert

logger = get_logger("setting")

SETTING_TYPES = {"string", "int", "float", "bool", "json"}


def parse_value(value: Optional[str], setting_type: Optional[str]) -> Any:
    """按 setting_type 解析字符串值；解析失败时原样返回，不抛错"""
    if value is None:
        return None
    kind = (setting_type or "string").lower()
    try:
        if kind == "int":
            return int(value)
        if kind == "float":
            return float(value)
        if kind == "bool":
            return str(value).strip().lower() in {"1", "true", "yes", "on"}
        if kind == "json":
            return json.loads(value)
    except (ValueError, TypeError, json.JSONDecodeError):
        logger.warning("配置项解析失败 type=%s value=%r，按原字符串返回", kind, value)
    return value


def _out(setting: SystemSettings) -> dict:
    return {
        "id": setting.id,
        "setting_key": setting.setting_key,
        "setting_value": setting.setting_value,
        "parsed_value": parse_value(setting.setting_value, setting.setting_type),
        "setting_type": setting.setting_type,
        "description": setting.description,
        "is_public": bool(setting.is_public),
        "created_at": setting.created_at,
        "updated_at": setting.updated_at,
    }


class SettingService:
    """系统配置读写"""

    def _validate_type(self, setting_type: Optional[str]) -> str:
        kind = (setting_type or "string").lower()
        if kind not in SETTING_TYPES:
            raise BadRequestError(f"不支持的 setting_type: {kind}（可选 {sorted(SETTING_TYPES)}）")
        return kind

    async def list_settings(
        self,
        db: AsyncSession,
        *,
        is_public: Optional[bool] = None,
        keyword: Optional[str] = None,
    ) -> List[dict]:
        settings, _total = await setting_crud.list(
            db, page=1, page_size=0, keyword=keyword, filters={"is_public": is_public},
            order_by="id", order="asc",
        )
        return [_out(setting) for setting in settings]

    async def get_setting(self, db: AsyncSession, key: str) -> dict:
        setting = await setting_crud.get_by(db, setting_key=key)
        if setting is None:
            raise NotFoundError(f"配置项 {key} 不存在")
        return _out(setting)

    async def public_settings(self, db: AsyncSession) -> dict:
        """公开配置（前端可读，无需权限）"""
        settings, _total = await setting_crud.list(
            db, page=1, page_size=0, filters={"is_public": True}, order_by="id", order="asc"
        )
        return {
            setting.setting_key: parse_value(setting.setting_value, setting.setting_type)
            for setting in settings
        }

    async def upsert(
        self,
        db: AsyncSession,
        key: str,
        *,
        value: Optional[str] = None,
        setting_type: Optional[str] = None,
        description: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> dict:
        kind = self._validate_type(setting_type) if setting_type else None
        setting = await setting_crud.get_by(db, setting_key=key)

        if setting is None:
            setting = await setting_crud.create(
                db,
                {
                    "setting_key": key,
                    "setting_value": value,
                    "setting_type": kind or "string",
                    "description": description,
                    "is_public": bool(is_public),
                },
            )
            return _out(setting)

        data: dict = {"setting_value": value}
        if kind:
            data["setting_type"] = kind
        if description is not None:
            data["description"] = description
        if is_public is not None:
            data["is_public"] = is_public
        setting = await setting_crud.update(db, setting, data)
        return _out(setting)

    async def batch_upsert(self, db: AsyncSession, items: Sequence[SettingUpsert]) -> List[dict]:
        result = []
        for item in items:
            result.append(
                await self.upsert(
                    db,
                    item.setting_key,
                    value=item.setting_value,
                    setting_type=item.setting_type,
                    description=item.description,
                    is_public=item.is_public,
                )
            )
        return result

    async def delete_setting(self, db: AsyncSession, key: str) -> None:
        setting = await setting_crud.get_by(db, setting_key=key)
        if setting is None:
            raise NotFoundError(f"配置项 {key} 不存在")
        await setting_crud.remove(db, setting)


setting_service = SettingService()
