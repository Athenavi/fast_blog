"""ai.config 模块业务逻辑：AI 提供商配置（凭据脱敏）

加密格式见 ``core/secret_box.py``：base64(nonce(12B) + ciphertext + tag)，
密钥 = SHA256(SECRET_KEY)（与 ops/cdn、third_party_publish 共用同一实现）。
本模块**只加密、不解密**（响应只回 has_api_key），
因此 SECRET_KEY 轮换不会破坏管理功能，但二期执行引擎解密密钥时需固定 SECRET_KEY。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import ConflictError, NotFoundError
from src.api.v3.core.secret_box import encrypt_secret
from src.api.v3.modules.ai.config.crud import ai_config_crud
from src.api.v3.modules.ai.config.schema import AIConfigCreate, AIConfigOut, AIConfigUpdate


def _to_out(row) -> dict:
    data = AIConfigOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["has_api_key"] = bool(getattr(row, "api_key_encrypted", None))
    return data


class AIConfigService:
    """AI 配置管理（ai 域，管理端跨用户）"""

    async def list_configs(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        user_id: Optional[int] = None, provider: Optional[str] = None,
        is_active: Optional[bool] = None, keyword: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await ai_config_crud.list(
            db, page=page, page_size=page_size, keyword=keyword,
            filters={"user_id": user_id, "provider": provider, "is_active": is_active},
        )
        return [_to_out(r) for r in rows], total

    async def create_config(self, db: AsyncSession, payload: AIConfigCreate) -> dict:
        if await ai_config_crud.exists(db, user_id=payload.user_id, name=payload.name):
            raise ConflictError(f"该用户下已存在同名配置: {payload.name}")
        data = payload.model_dump() | {
            "api_key_encrypted": encrypt_secret(payload.api_key),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        data.pop("api_key", None)
        row = await ai_config_crud.create(db, data)
        return _to_out(row)

    async def update_config(self, db: AsyncSession, config_id: int, payload: AIConfigUpdate) -> dict:
        row = await ai_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("AI 配置不存在")
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] and data["name"] != row.name:
            if await ai_config_crud.exists(db, user_id=row.user_id, name=data["name"]):
                raise ConflictError(f"该用户下已存在同名配置: {data['name']}")
        if data.get("api_key"):
            data["api_key_encrypted"] = encrypt_secret(data.pop("api_key"))
        else:
            data.pop("api_key", None)  # 留空保持原值
        updated = await ai_config_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _to_out(updated)

    async def delete_config(self, db: AsyncSession, config_id: int) -> None:
        row = await ai_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("AI 配置不存在")
        await ai_config_crud.remove(db, row)


ai_config_service = AIConfigService()
