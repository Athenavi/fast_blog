"""ops.cdn 模块业务逻辑：CDN 配置（持久化到 system_settings，凭据脱敏）

存储键：``cdn.config``（setting_type=json，is_public=False —— 不进公开配置端点）。
脱敏策略：落库前把 ``api_token`` 明文加密为 AES-256-GCM（与 ai/config 同格式）；
读取时永不回传，只回 ``has_api_token``。更新时 api_token 留空保持原值。
"""

import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.ops.cdn.schema import CDNConfigOut, CDNConfigPayload, SUPPORTED_PROVIDERS
from src.api.v3.modules.system.setting.service import setting_service

CDN_SETTING_KEY = "cdn.config"


def _encrypt_secret(raw: str) -> str:
    from shared.config.settings import settings

    key = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, raw.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def _mask(config: dict) -> dict:
    """响应脱敏：token 永不回传，只回 has_api_token"""
    out = {k: v for k, v in config.items() if k != "api_token_encrypted"}
    out["has_api_token"] = bool(config.get("api_token_encrypted"))
    return out


class CDNService:
    """CDN 配置（ops 域，无表 —— 复用 system_settings 存储）"""

    async def get_config(self, db: AsyncSession) -> dict:
        try:
            setting = await setting_service.get_setting(db, CDN_SETTING_KEY)
        except Exception:  # noqa: BLE001 - 键不存在时返回默认空配置
            return _mask({"is_active": False})
        config = setting.get("parsed_value") or {}
        return _mask(config)

    async def save_config(self, db: AsyncSession, payload: CDNConfigPayload) -> dict:
        if payload.provider not in SUPPORTED_PROVIDERS:
            raise BadRequestError(
                f"不支持的 CDN 提供商: {payload.provider}（可选 {list(SUPPORTED_PROVIDERS)}）"
            )
        existing: dict = {}
        try:
            setting = await setting_service.get_setting(db, CDN_SETTING_KEY)
            existing = setting.get("parsed_value") or {}
        except Exception:  # noqa: BLE001 - 首次保存
            existing = {}

        data = payload.model_dump(mode="json", exclude_unset=True)
        if data.get("api_token"):
            data["api_token_encrypted"] = _encrypt_secret(data.pop("api_token"))
        else:
            data.pop("api_token", None)  # 留空保持原值
        data["updated_at"] = _now_iso()
        merged = {**existing, **data}

        await setting_service.upsert(
            db,
            CDN_SETTING_KEY,
            value=json.dumps(merged, ensure_ascii=False),
            setting_type="json",
            description="CDN 配置（ops/cdn 模块管理，api_token 已加密）",
            is_public=False,
        )
        out: dict = CDNConfigOut.model_validate(_mask(merged)).model_dump(mode="json")
        return out


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


cdn_service = CDNService()
