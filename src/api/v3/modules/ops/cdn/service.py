"""ops.cdn 模块业务逻辑：CDN 配置（持久化到 system_settings，凭据脱敏）

存储键：``cdn.config``（setting_type=json，is_public=False —— 不进公开配置端点）。
脱敏策略：落库前把 ``api_token`` 明文加密为 AES-256-GCM（``core/secret_box.py``，
与 ai/config、third_party_publish 共用同一实现）；
读取时永不回传，只回 ``has_api_token``。更新时 api_token 留空保持原值。
"""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.secret_box import decrypt_secret, encrypt_secret
from src.api.v3.modules.ops.cdn import remote as cdn_remote
from src.api.v3.modules.ops.cdn.schema import (
    CDNConfigOut,
    CDNConfigPayload,
    CDNPurgePayload,
    CDNPurgeResult,
    SUPPORTED_PROVIDERS,
)
from src.api.v3.modules.system.setting.service import setting_service

CDN_SETTING_KEY = "cdn.config"


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
            data["api_token_encrypted"] = encrypt_secret(data.pop("api_token"))
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

    # ------------------------------------------------------------ 远端动作
    async def _raw_config(self, db: AsyncSession) -> dict:
        """取未脱敏的原始配置（含密文），供远端调用使用"""
        try:
            setting = await setting_service.get_setting(db, CDN_SETTING_KEY)
        except Exception:  # noqa: BLE001 - 键不存在时按"未配置"处理
            return {}
        value = setting.get("parsed_value") or {}
        return value if isinstance(value, dict) else {}

    def _token_for(self, provider: str, config: dict) -> str:
        """按需解密凭据：**只有 cloudflare 需要 token**，其它 provider 不去碰密文

        历史密文可能因 SECRET_KEY 变更而解不开；那时只有真正需要它的 provider 才报错，
        不会把 custom / 未实现 provider 的诊断信息掩盖成"凭据解密失败"。
        """
        if provider != "cloudflare":
            return ""
        encrypted = str(config.get("api_token_encrypted") or "")
        if not encrypted:
            return ""
        try:
            return decrypt_secret(encrypted)
        except ValueError as exc:
            raise BadRequestError(
                "CDN 凭据无法解密（SECRET_KEY 变更或数据损坏）；请在 CDN 配置页重新填写 api_token"
            ) from exc

    async def _provider_or_400(self, db: AsyncSession) -> tuple[str, dict]:
        config = await self._raw_config(db)
        provider = str(config.get("provider") or "").strip()
        if not provider:
            raise BadRequestError("尚未配置 CDN 提供商（provider），无法执行远端动作")
        return provider, config

    async def purge(self, db: AsyncSession, payload: CDNPurgePayload) -> dict:
        """清缓存（真实调用厂商 API；未实现/未配置一律明确报错）"""
        provider, config = await self._provider_or_400(db)
        result = await cdn_remote.purge(
            provider=provider,
            config=config,
            token=self._token_for(provider, config),
            urls=list(payload.urls),
            purge_everything=payload.purge_everything,
        )
        return CDNPurgeResult.model_validate(result).model_dump(mode="json")

    async def preheat(self, db: AsyncSession, payload: CDNPurgePayload) -> dict:
        """预热（cloudflare 无此接口 → 如实报错）"""
        provider, config = await self._provider_or_400(db)
        result = await cdn_remote.preheat(
            provider=provider,
            config=config,
            token=self._token_for(provider, config),
            urls=list(payload.urls),
        )
        return CDNPurgeResult.model_validate(result).model_dump(mode="json")


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


cdn_service = CDNService()
