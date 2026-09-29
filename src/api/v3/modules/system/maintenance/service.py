"""维护模式：配置持久化 + 定时窗口 + IP 白名单（任务 14c）

v2 的 ``shared/services/system/maintenance_mode.py`` 有两个问题：

1. **配置存文件**（``storage/maintenance_mode.json``）→ v3 落 ``system_settings``；
2. **``is_maintenance_mode()`` 有写副作用**：判断"是否在维护窗口内"时会顺手
   ``save_config()`` 改 ``enabled`` —— 一次读操作变成一次写（并发下互相覆盖，
   而且中间件每请求都会调它）。v3 把"是否生效"改成**纯计算**：
   ``enabled`` 是人工开关，``in_schedule`` 是当前时间落在定时窗口内，两者取或。

配置结构沿用 v2：``enabled`` / ``message`` / ``whitelist_ips`` /
``scheduled_start`` / ``scheduled_end`` / ``retry_after``。
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger

logger = get_logger("system.maintenance")

#: 配置在 ``system_settings`` 里的键
CONFIG_KEY = "maintenance.config"

DEFAULT_MESSAGE = "系统正在维护中，请稍后访问"

#: 默认配置（字段与 v2 一致）
DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "message": DEFAULT_MESSAGE,
    "whitelist_ips": [],
    "scheduled_start": None,
    "scheduled_end": None,
    "retry_after": 3600,
}

#: 维护期间仍可访问的路径前缀（管理员要能登录、探针要能探测、状态要能查）
ALLOWED_PATH_PREFIXES: Tuple[str, ...] = (
    "/api/v3/health",
    "/api/v3/system/auth/login",
    "/api/v3/system/auth/refresh",
    "/api/v3/system/maintenance",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
)


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    """解析 ISO 时间（兼容 ``Z`` 结尾与无时区），失败返回 None"""
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class MaintenanceService:
    """维护模式配置与状态计算"""

    # ------------------------------------------------------------------ 配置
    async def get_config(self, db: AsyncSession) -> Dict[str, Any]:
        from shared.models.system.system_settings import SystemSettings

        row = (
            await db.execute(
                select(SystemSettings).where(SystemSettings.setting_key == CONFIG_KEY).limit(1)
            )
        ).scalars().first()
        stored: Dict[str, Any] = {}
        if row is not None and row.setting_value:
            try:
                parsed = json.loads(row.setting_value)
            except ValueError:
                logger.warning("维护模式配置不是合法 JSON，按默认值处理")
                parsed = None
            if isinstance(parsed, dict):
                stored = parsed
        return {**DEFAULT_CONFIG, **{k: v for k, v in stored.items() if k in DEFAULT_CONFIG}}

    async def save_config(
        self, db: AsyncSession, payload: Dict[str, Any], *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """保存配置（未知键、非法时间、非法 retry_after 一律 400）"""
        from shared.models.system.system_settings import SystemSettings

        unknown = [key for key in payload if key not in DEFAULT_CONFIG]
        if unknown:
            raise BadRequestError(f"未知配置项：{unknown}（可选：{sorted(DEFAULT_CONFIG)}）")

        if "retry_after" in payload:
            try:
                retry_after = int(payload["retry_after"])
            except (TypeError, ValueError) as exc:
                raise BadRequestError("retry_after 必须是整数秒") from exc
            if retry_after < 0 or retry_after > 86400 * 7:
                raise BadRequestError("retry_after 需在 0 ~ 604800 秒之间")
            payload = {**payload, "retry_after": retry_after}

        for key in ("scheduled_start", "scheduled_end"):
            if key in payload and payload[key]:
                if parse_iso(payload[key]) is None:
                    raise BadRequestError(f"{key} 不是合法的 ISO 时间")
        start = parse_iso(payload.get("scheduled_start"))
        end = parse_iso(payload.get("scheduled_end"))
        if start and end and end <= start:
            raise BadRequestError("scheduled_end 必须晚于 scheduled_start")

        if "whitelist_ips" in payload:
            raw = payload["whitelist_ips"] or []
            if not isinstance(raw, (list, tuple)):
                raise BadRequestError("whitelist_ips 必须是数组")
            payload = {**payload, "whitelist_ips": [str(item).strip() for item in raw if str(item).strip()]}

        merged = {**(await self.get_config(db)), **{k: v for k, v in payload.items() if k in DEFAULT_CONFIG}}

        row = (
            await db.execute(
                select(SystemSettings).where(SystemSettings.setting_key == CONFIG_KEY).limit(1)
            )
        ).scalars().first()
        now = datetime.now()
        value = json.dumps(merged, ensure_ascii=False)
        if row is None:
            db.add(
                SystemSettings(
                    setting_key=CONFIG_KEY,
                    setting_value=value,
                    setting_type="json",
                    description="维护模式配置",
                    is_public=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.setting_value = value
            row.setting_type = "json"
            row.is_public = True
            row.updated_at = now
        await db.commit()
        logger.info("维护模式配置已更新（用户 %s）：%s", user_id, sorted(payload))
        return merged

    # ------------------------------------------------------------------ 状态
    @staticmethod
    def evaluate(config: Dict[str, Any], *, client_ip: Optional[str] = None,
                 now: Optional[datetime] = None) -> Dict[str, Any]:
        """**纯计算**当前是否处于维护（不写配置）"""
        now = now or datetime.now(timezone.utc)
        merged = {**DEFAULT_CONFIG, **config}
        start = parse_iso(merged.get("scheduled_start"))
        end = parse_iso(merged.get("scheduled_end"))
        in_schedule = bool(start and end and start <= now <= end)
        whitelist = [str(item) for item in (merged.get("whitelist_ips") or [])]
        whitelisted = bool(client_ip) and str(client_ip) in whitelist
        enabled = bool(merged.get("enabled"))

        return {
            "active": (enabled or in_schedule) and not whitelisted,
            "enabled": enabled,
            "in_schedule": in_schedule,
            "whitelisted": whitelisted,
            "message": merged.get("message") or DEFAULT_MESSAGE,
            "retry_after": int(merged.get("retry_after") or 3600),
            "scheduled_start": merged.get("scheduled_start"),
            "scheduled_end": merged.get("scheduled_end"),
            "whitelist_ips": whitelist,
            "checked_at": now.isoformat(),
        }

    async def status(self, db: AsyncSession, *, client_ip: Optional[str] = None) -> Dict[str, Any]:
        return self.evaluate(await self.get_config(db), client_ip=client_ip)

    # ------------------------------------------------------------------ 操作
    async def enable(
        self,
        db: AsyncSession,
        *,
        message: Optional[str] = None,
        whitelist_ips: Optional[List[str]] = None,
        retry_after: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"enabled": True}
        if message:
            payload["message"] = message
        if whitelist_ips is not None:
            payload["whitelist_ips"] = whitelist_ips
        if retry_after is not None:
            payload["retry_after"] = retry_after
        return await self.save_config(db, payload, user_id=user_id)

    async def disable(self, db: AsyncSession, *, user_id: Optional[int] = None) -> Dict[str, Any]:
        return await self.save_config(db, {"enabled": False}, user_id=user_id)

    async def update_message(
        self, db: AsyncSession, message: str, *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if not (message or "").strip():
            raise BadRequestError("维护提示语不能为空")
        return await self.save_config(db, {"message": message.strip()}, user_id=user_id)

    async def schedule(
        self,
        db: AsyncSession,
        *,
        start: str,
        end: str,
        message: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """设置定时维护窗口（到点自动生效/失效，无需再改配置）"""
        payload: Dict[str, Any] = {"scheduled_start": start, "scheduled_end": end}
        if message:
            payload["message"] = message
        return await self.save_config(db, payload, user_id=user_id)

    async def add_whitelist_ip(
        self, db: AsyncSession, ip: str, *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        target = (ip or "").strip()
        if not target:
            raise BadRequestError("IP 不能为空")
        config = await self.get_config(db)
        whitelist = list(config.get("whitelist_ips") or [])
        if target in whitelist:
            raise BadRequestError(f"IP {target} 已在白名单中")
        whitelist.append(target)
        return await self.save_config(db, {"whitelist_ips": whitelist}, user_id=user_id)

    async def remove_whitelist_ip(
        self, db: AsyncSession, ip: str, *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        target = (ip or "").strip()
        config = await self.get_config(db)
        whitelist = [item for item in (config.get("whitelist_ips") or []) if item != target]
        if len(whitelist) == len(config.get("whitelist_ips") or []):
            raise BadRequestError(f"IP {target} 不在白名单中")
        return await self.save_config(db, {"whitelist_ips": whitelist}, user_id=user_id)


maintenance_service = MaintenanceService()
