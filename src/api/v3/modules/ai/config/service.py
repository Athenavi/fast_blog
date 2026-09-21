"""ai.config 模块业务逻辑：AI 提供商配置（凭据按用户加密 + 真实连接测试）

**凭据加密与「用户密码 + app_secret_key」双因子挂钩**：密钥 = ``HKDF-SECRET_KEY(salt=用户密码哈希)``，
实现见 ``core/user_secret_box.py``。由此带来的行为（都是刻意的）：

  - 服务端**不需要用户明文密码**（派生只用库里已有的 ``users.password`` 哈希）→
    后台/定时执行也能解密；
  - 用户**改密码后**其既有 api_key 解不开 → 这里如实报"请重新填写"，绝不静默当空值；
  - 不同用户的密文互不可解（一用户一密钥）。

「用户自定义连接」的字段都在本模块暴露：``provider`` 决定协议（openai 兼容系 / anthropic），
``api_url`` / ``model`` / ``api_version`` / ``extra_headers`` / ``max_tokens`` 全部可自定义。
"""

import json
import time
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.user_secret_box import decrypt_for_user, encrypt_for_user
from src.api.v3.modules.ai import llm
from src.api.v3.modules.ai.config.crud import ai_config_crud
from src.api.v3.modules.ai.config.schema import AIConfigCreate, AIConfigUpdate


def _parse_extra_headers(raw: Any) -> dict[str, str]:
    """库里的 extra_headers 是 JSON 文本 → 请求头字典（坏数据明确报错，不糊成空字典）"""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    try:
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001 - 明确告诉调用方哪里坏了
        raise BadRequestError(f"extra_headers 不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise BadRequestError("extra_headers 必须是 JSON 对象")
    return {str(key): str(value) for key, value in data.items()}


def _dump_extra_headers(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        # 允许直接传 JSON 文本（校验一下），或空串表示清空
        if not value.strip():
            return None
        try:
            parsed = json.loads(value)
        except Exception as exc:  # noqa: BLE001
            raise BadRequestError(f"extra_headers 不是合法 JSON：{exc}") from exc
        if not isinstance(parsed, dict):
            raise BadRequestError("extra_headers 必须是 JSON 对象")
        return json.dumps({str(k): str(v) for k, v in parsed.items()}, ensure_ascii=False)
    if not isinstance(value, dict):
        raise BadRequestError("extra_headers 必须是 JSON 对象")
    return json.dumps({str(k): str(v) for k, v in value.items()}, ensure_ascii=False)


def _to_out(row) -> dict:
    """脱敏出参：api_key 永不回传，只回 has_api_key"""
    return {
        "id": row.id,
        "user_id": row.user_id,
        "name": row.name,
        "api_url": row.api_url,
        "has_api_key": bool(row.api_key_encrypted),
        "model": row.model,
        "provider": row.provider,
        "api_version": row.api_version,
        "extra_headers": _parse_extra_headers(row.extra_headers) or None,
        "max_tokens": int(row.max_tokens or 1024),
        "is_active": row.is_active,
        "sort_order": row.sort_order,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


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
        password_hash = await self._user_password_hash(db, payload.user_id)
        data = payload.model_dump()
        data["api_key_encrypted"] = encrypt_for_user(payload.api_key, password_hash)
        data["extra_headers"] = _dump_extra_headers(payload.extra_headers)
        data.pop("api_key", None)
        data["created_at"] = datetime.now()
        data["updated_at"] = datetime.now()
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
            password_hash = await self._user_password_hash(db, row.user_id)
            data["api_key_encrypted"] = encrypt_for_user(data.pop("api_key"), password_hash)
        else:
            data.pop("api_key", None)  # 留空保持原值
        if "extra_headers" in data:
            data["extra_headers"] = _dump_extra_headers(data["extra_headers"])
        updated = await ai_config_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _to_out(updated)

    async def delete_config(self, db: AsyncSession, config_id: int) -> None:
        row = await ai_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("AI 配置不存在")
        await ai_config_crud.remove(db, row)

    # ------------------------------------------------------------------ 真实调用
    async def resolve_llm_settings(self, db: AsyncSession, config_id: int) -> llm.LLMSettings:
        """取某个配置的可用连接设置（**含解密后的 api_key**），供测试连接与工作流执行复用"""
        row = await ai_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("AI 配置不存在")
        password_hash = await self._user_password_hash(db, row.user_id)
        try:
            api_key = decrypt_for_user(row.api_key_encrypted, password_hash)
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc
        return llm.LLMSettings(
            provider=row.provider or "openai",
            api_url=row.api_url or "",
            api_key=api_key,
            model=row.model or "",
            api_version=row.api_version,
            extra_headers=_parse_extra_headers(row.extra_headers),
            max_tokens=int(row.max_tokens or 1024),
        )

    async def test_connection(self, db: AsyncSession, config_id: int) -> dict:
        """**真实**调一次模型验证连通性（失败会带上厂商返回的原因）"""
        settings = await self.resolve_llm_settings(db, config_id)
        started = time.time()
        result = await llm.complete(
            settings,
            system="你是连接测试助手。",
            prompt="请只回复两个字：正常",
            max_tokens=32,
        )
        return {
            "ok": True,
            "provider": settings.provider,
            "protocol": result.protocol,
            "model": result.model,
            "reply": (result.text or "")[:200],
            "latency_ms": int((time.time() - started) * 1000),
            "usage": {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
            },
        }

    # ------------------------------------------------------------------ 内部
    async def _user_password_hash(self, db: AsyncSession, user_id: int) -> str:
        from shared.models.user.user import User

        user = await db.get(User, user_id)
        if user is None:
            raise NotFoundError(f"用户不存在：{user_id}")
        return user.password or ""


ai_config_service = AIConfigService()
