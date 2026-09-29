"""chat.web_push 模块业务逻辑：浏览器推送订阅登记 / 退订 / 推送 / 统计 / 清理。

源能力来自 v2 的 ``shared/services/chat/web_push_service.py``。**与 v2 的差异**：

====================  v2 的做法                                      问题                                          本模块
存储                 模块级 ``self._subscriptions = {}``（进程内 dict）  重启即失、多 worker 各一份、单进程假实现      真表落库：``system_settings``（JSON 配置键，每用户一行）
发送                  ``pywebpush`` + VAPID（缺失时诚实返回 False）       ——                                            保留「诚实失败」：缺库 / 缺密钥时端点**返回未配置错误**，绝不伪造成功
订阅校验              仅查 endpoint 去重，不校验 keys                    非法订阅可入库                                 ``subscription_issue`` 纯函数校验 endpoint(https)+keys(p256dh/auth)
失效清理              ``cleanup_invalid_subscriptions`` 是**死循环**（``cutoff`` 算了却没用，永远清 0）  形同虚设            ``cleanup_ids`` 纯函数按 ``created_at`` 真实判定过期 / 结构非法并真删
统计                  ``get_subscription_stats`` 从内存 dict 算             重启归零                                      ``stats`` 从 ``system_settings`` 真聚合
VAPID 配置            ``configure_vapid_keys`` 进程内改内存              重启丢失、任意调用者都能改密钥                  从环境变量读；**不提供**运行时改密钥端点（避免越权改密钥）
====================  =========  ==========  =====

**如实降级（无专表）**：本项目**没有** push 订阅相关的 ORM 模型 / 数据库表，且本任务不得新建表。
因此订阅复用了既有的 ``system_settings`` 表（``setting_value`` 是 Text，存 JSON；同 ``screen_options`` /
``help`` 的既有模式）：每个用户一行，``setting_key = chat.web_push.subscriptions.{user_id}``，
``setting_value`` 是订阅记录数组。这是**如实降级**，不是把内存搬个地方 —— 数据真实持久化、多 worker 共享。

**推送发送必须真实**：发送依赖 ``pywebpush`` 库 + VAPID 密钥（环境变量
``WEB_PUSH_VAPID_PUBLIC_KEY`` / ``WEB_PUSH_VAPID_PRIVATE_KEY`` / ``WEB_PUSH_VAPID_SUBJECT``）。
二者缺一时，发送端点抛 ``BadRequestError``（HTTP 200 + ``code=400``，消息说明缺什么），
**不会**返回假的 "sent_count"。

纯函数（``is_push_configured`` / ``is_valid_vapid_public_key`` / ``subscription_issue`` /
``build_payload`` / ``payload_digest`` / ``build_subscription_record`` / ``is_expired_subscription`` /
``cleanup_ids`` / ``summarize_subscriptions``）与 DB / 网络操作彻底分离，便于无库测试。
"""

import asyncio
import base64
import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.system.system_settings import SystemSettings
from shared.models.user import User as UserModel
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.chat.web_push.schema import (
    WebPushBroadcastIn,
    WebPushCleanupOut,
    WebPushSendIn,
    WebPushSendResponse,
    WebPushSendResult,
    WebPushStatsOut,
    WebPushSubscriptionIn,
    WebPushSubscriptionOut,
    WebPushUnsubscribeIn,
)

logger = get_logger("chat.web_push")

#: ``system_settings.setting_key`` 前缀：``chat.web_push.subscriptions.{user_id}``
STORAGE_PREFIX = "chat.web_push.subscriptions."

#: 通知默认图标 / 徽章（与 v2 payload 一致）
DEFAULT_ICON = "/favicon.ico"
DEFAULT_BADGE = "/icons/badge-72x72.png"

#: 通知动作按钮（与 v2 payload 一致）
PAYLOAD_ACTIONS: tuple[dict[str, str], ...] = (
    {"action": "open", "title": "查看"},
    {"action": "dismiss", "title": "关闭"},
)

#: VAPID subject 默认值（与 v2 一致）
DEFAULT_SUBJECT = "mailto:admin@localhost"

#: 推送服务返回这两个状态码代表订阅已失效，应清理（与 v2 一致）
EXPIRED_STATUS_CODES = (404, 410)


# ============================================================
# 纯函数：VAPID / 配置
# ============================================================
def _import_webpush() -> Any:
    """尝试导入 ``pywebpush``；未安装时返回 ``None``（不抛错）"""
    try:  # pragma: no cover - 取决于运行环境是否安装
        import pywebpush

        return pywebpush
    except ImportError:  # pragma: no cover
        return None


def _b64url_decode(value: str) -> Optional[bytes]:
    """宽松的 base64url 解码（自动补齐 padding）；失败返回 ``None``"""
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    padding = "=" * (-len(text) % 4)
    try:
        return base64.urlsafe_b64decode(text + padding)
    except (ValueError, TypeError):
        return None


def is_valid_vapid_public_key(key: Optional[str]) -> bool:
    """校验 VAPID 公钥形状（**纯函数**）

    VAPID 公钥是一段 base64url 编码的 **uncompressed P-256 公钥**：解码后应为 65 字节
    且首字节 ``0x04``。形状不对（长度不符 / 解码失败 / 前缀不对）判为无效。
    """
    raw = _b64url_decode(key or "")
    return bool(raw is not None and len(raw) == 65 and raw[0] == 0x04)


def is_push_configured(
    public_key: Optional[str],
    private_key: Optional[str],
    *,
    webpush_available: bool,
) -> bool:
    """推送是否可用于**真实发送**（**纯函数**）

    三个前提缺一不可：``pywebpush`` 可用、VAPID 公钥与私钥都非空。
    """
    return bool(webpush_available and public_key and private_key)


@dataclass(frozen=True)
class WebPushConfig:
    """Web Push 运行配置（来自环境变量 + 库可用性探测）"""

    public_key: str = ""
    private_key: str = ""
    subject: str = DEFAULT_SUBJECT
    webpush_available: bool = False

    @property
    def configured(self) -> bool:
        """是否可真实发送"""
        return is_push_configured(
            self.public_key, self.private_key, webpush_available=self.webpush_available
        )

    def reason(self) -> str:
        """不能发送时的**如实**原因（供 400 消息与公钥下发端点使用）"""
        if not self.webpush_available:
            return "pywebpush 未安装（安装并配置 VAPID 密钥后才能真实推送）"
        if not self.private_key:
            return "缺少 VAPID 私钥（环境变量 WEB_PUSH_VAPID_PRIVATE_KEY）"
        if not self.public_key:
            return "缺少 VAPID 公钥（环境变量 WEB_PUSH_VAPID_PUBLIC_KEY）"
        return "已配置"


def load_web_push_config() -> WebPushConfig:
    """从环境变量 + ``pywebpush`` 可用性构造运行配置（**无 DB / 无网络**）

    与 v2 的 ``WebPushService.__init__`` 同名含义一致；v2 的 ``configure_vapid_keys``
    （运行时改内存密钥）在 v3 **不提供** —— 生产通过环境变量配置，避免越权改密钥。
    """
    return WebPushConfig(
        public_key=(os.environ.get("WEB_PUSH_VAPID_PUBLIC_KEY", "") or "").strip(),
        private_key=(os.environ.get("WEB_PUSH_VAPID_PRIVATE_KEY", "") or "").strip(),
        subject=(os.environ.get("WEB_PUSH_VAPID_SUBJECT", "") or "").strip() or DEFAULT_SUBJECT,
        webpush_available=_import_webpush() is not None,
    )


# ============================================================
# 纯函数：订阅结构 / 载荷 / 清理 / 统计
# ============================================================
def subscription_issue(subscription: Any) -> Optional[str]:
    """返回订阅数据的**第一个**问题；合法时返回 ``None``（**纯函数**）

    校验：是 dict、``endpoint`` 是 https、``keys`` 含非空 ``p256dh`` 与 ``auth``。
    """
    if not isinstance(subscription, dict):
        return "订阅数据必须是 JSON 对象"
    endpoint = subscription.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.strip():
        return "缺少 endpoint"
    if not endpoint.startswith("https://"):
        return "endpoint 必须是 https 地址"
    keys = subscription.get("keys")
    if not isinstance(keys, dict):
        return "缺少订阅 keys"
    for field in ("p256dh", "auth"):
        value = keys.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"缺少 keys.{field}"
    return None


def is_valid_subscription(subscription: Any) -> bool:
    """订阅结构是否合法（**纯函数**，``subscription_issue`` 取反）"""
    return subscription_issue(subscription) is None


def build_subscription_record(
    subscription: dict,
    *,
    subscription_id: str,
    now_iso: str,
    user_agent: Optional[str] = None,
) -> dict:
    """由合法订阅数据构造一条落库记录（**纯函数**，时间由调用方注入）

    不校验合法性（调用方先用 ``subscription_issue`` 把关）；只做字段收敛。
    """
    keys = subscription.get("keys") or {}
    return {
        "id": subscription_id,
        "endpoint": subscription.get("endpoint"),
        "keys": {
            "p256dh": keys.get("p256dh"),
            "auth": keys.get("auth"),
        },
        "user_agent": (user_agent or subscription.get("user_agent") or "")[:512],
        "created_at": now_iso,
        "last_sent_at": None,
        "send_count": 0,
        "fail_count": 0,
    }


def build_payload(
    title: str,
    body: str,
    *,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    data: Optional[dict] = None,
    timestamp: Optional[str] = None,
) -> dict:
    """构造通知 payload（**纯函数**，与 v2 结构一致；时间由调用方注入）"""
    return {
        "title": title,
        "body": body,
        "icon": icon or DEFAULT_ICON,
        "badge": badge or DEFAULT_BADGE,
        "data": dict(data or {}),
        "timestamp": timestamp,
        "actions": [dict(action) for action in PAYLOAD_ACTIONS],
    }


def payload_digest(payload: Any) -> str:
    """payload 的稳定 SHA-256 摘要（**纯函数**，键排序 + 紧凑分隔符）"""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def subscription_age_days(record: dict, now: datetime) -> Optional[float]:
    """订阅已存在的天数（**纯函数**，``now`` 由调用方注入；解析失败返回 ``None``）"""
    created = record.get("created_at") if isinstance(record, dict) else None
    if not created:
        return None
    try:
        created_dt = datetime.fromisoformat(created)
    except (TypeError, ValueError):
        return None
    return (now - created_dt).total_seconds() / 86400


def is_expired_subscription(record: dict, now: datetime, max_age_days: int) -> bool:
    """订阅是否「过期」（**纯函数**：存在天数 > ``max_age_days``；无法解析时间时不算过期）"""
    age = subscription_age_days(record, now)
    return bool(age is not None and age > max_age_days)


def cleanup_ids(records: list[dict], now: datetime, max_age_days: int) -> list[str]:
    """应被清理的订阅 ID 列表（**纯函数**）

    判定：记录已**过期**（``is_expired_subscription``）或**结构非法**（``subscription_issue``）。
    """
    removable: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        sub_id = record.get("id")
        if not sub_id:
            continue
        if is_expired_subscription(record, now, max_age_days) or not is_valid_subscription(record):
            removable.append(str(sub_id))
    return removable


def summarize_subscriptions(per_user: dict[int, list[dict]]) -> dict:
    """订阅统计（**纯函数**，入参为 ``{user_id: [record, ...]}``）

    ``total_users`` 记**有订阅的用户数**（键数量），``average_per_user`` = 平均每用户订阅数。
    """
    total_users = len(per_user)
    total_subscriptions = sum(len(items) for items in per_user.values())
    average = round(total_subscriptions / total_users, 4) if total_users else 0.0
    return {
        "total_users": total_users,
        "total_subscriptions": total_subscriptions,
        "average_per_user": average,
    }


# ============================================================
# 纯函数：推送库调用（无 DB；失败如实返回）
# ============================================================
def push_to_endpoint(
    record: dict,
    payload: dict,
    config: WebPushConfig,
) -> tuple[bool, Optional[int], Optional[str]]:
    """向单条订阅真实发送（**纯函数**，不发 DB 写；同步阻塞，调用方用线程池）

    返回 ``(success, status_code, error)``：

      - 成功 → ``(True, None, None)``
      - ``WebPushException`` → ``(False, <响应状态码或 None>, <消息>)``（410/404 由调用方判定失效）
      - 其它异常 → ``(False, None, <消息>)``

    **未配置时不会假装成功** —— 调用方应先经 ``is_push_configured`` 把关；本函数只在库可用时被调用。
    """
    webpush_mod = _import_webpush()
    if webpush_mod is None or not config.configured:
        return False, None, "web push 未配置"
    subscription_info = {
        "endpoint": record.get("endpoint"),
        "keys": {
            "p256dh": (record.get("keys") or {}).get("p256dh", ""),
            "auth": (record.get("keys") or {}).get("auth", ""),
        },
    }
    try:
        webpush_mod.webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=config.private_key,
            vapid_claims={"sub": config.subject},
        )
        return True, None, None
    except webpush_mod.WebPushException as exc:  # noqa: BLE001 - 需读取响应状态码判定失效
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return False, status, str(exc)
    except Exception as exc:  # noqa: BLE001 - 单端点异常不应中断整体推送
        return False, None, str(exc)


# ============================================================
# 服务（DB 读写）
# ============================================================
def storage_key(user_id: int) -> str:
    """该用户在 ``system_settings`` 里的键"""
    return f"{STORAGE_PREFIX}{user_id}"


def _user_id_of_key(key: str) -> Optional[int]:
    """从 ``chat.web_push.subscriptions.{id}`` 解析 user_id（非法返回 ``None``）"""
    if not key or not key.startswith(STORAGE_PREFIX):
        return None
    suffix = key[len(STORAGE_PREFIX):]
    return int(suffix) if suffix.isdigit() else None


def _out(record: dict) -> dict:
    """把落库记录转成对外模型（**不暴露 keys 公钥材料**）"""
    return WebPushSubscriptionOut(
        id=str(record.get("id") or ""),
        endpoint=str(record.get("endpoint") or ""),
        user_agent=record.get("user_agent") or None,
        created_at=record.get("created_at"),
        last_sent_at=record.get("last_sent_at"),
        send_count=int(record.get("send_count") or 0),
        fail_count=int(record.get("fail_count") or 0),
    ).model_dump(mode="json")


class WebPushService:
    """Web Push 订阅与推送（chat 域）"""

    # ------------------------------------------------------------ 存储
    async def _load(self, db: AsyncSession, user_id: int) -> list[dict]:
        """读出某用户的全部订阅（缺失 / 损坏时返回空列表）"""
        row = (
            await db.execute(
                select(SystemSettings)
                .where(SystemSettings.setting_key == storage_key(user_id))
                .limit(1)
            )
        ).scalars().first()
        return _parse_records(row.setting_value if row is not None else None)

    async def _save(self, db: AsyncSession, user_id: int, records: list[dict]) -> None:
        """写回某用户的订阅（空列表则删除该行）"""
        key = storage_key(user_id)
        row = (
            await db.execute(
                select(SystemSettings).where(SystemSettings.setting_key == key).limit(1)
            )
        ).scalars().first()
        now = datetime.now()
        if not records:
            if row is not None:
                await db.delete(row)
                await db.commit()
            return
        value = json.dumps(records, ensure_ascii=False)
        if row is None:
            db.add(
                SystemSettings(
                    setting_key=key,
                    setting_value=value,
                    setting_type="json",
                    description=f"用户 {user_id} 的 Web Push 订阅",
                    is_public=False,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.setting_value = value
            row.setting_type = "json"
            row.updated_at = now
        await db.commit()

    async def _all_by_user(self, db: AsyncSession) -> dict[int, list[dict]]:
        """读出**全部**用户的订阅（``{user_id: [record, ...]}``，坏数据行忽略）"""
        rows = (
            await db.execute(
                select(SystemSettings).where(
                    SystemSettings.setting_key.like(f"{STORAGE_PREFIX}%")
                )
            )
        ).scalars().all()
        result: dict[int, list[dict]] = {}
        for row in rows:
            user_id = _user_id_of_key(row.setting_key or "")
            if user_id is None:
                continue
            records = _parse_records(row.setting_value)
            if records:
                result[user_id] = records
        return result

    # ------------------------------------------------------------ 发送前置校验
    @staticmethod
    def _ensure_sendable(config: WebPushConfig) -> None:
        """推送不可用时**如实**拒绝（HTTP 200 + code=400），绝不伪造成功"""
        if not config.configured:
            raise BadRequestError(f"Web Push 未配置，无法发送：{config.reason()}")

    # ------------------------------------------------------------ 订阅
    async def subscribe(
        self, db: AsyncSession, user_id: int, payload: WebPushSubscriptionIn
    ) -> dict:
        """登记（或更新）一条订阅；同一 endpoint 幂等（更新 keys / user_agent）"""
        data = payload.model_dump()
        issue = subscription_issue(data)
        if issue:
            raise BadRequestError(issue)

        records = await self._load(db, user_id)
        endpoint = payload.endpoint
        for record in records:
            if record.get("endpoint") == endpoint:
                record["keys"] = {
                    "p256dh": payload.keys.p256dh,
                    "auth": payload.keys.auth,
                }
                if payload.user_agent:
                    record["user_agent"] = payload.user_agent[:512]
                await self._save(db, user_id, records)
                return {"created": False, "subscription": _out(record)}

        record = build_subscription_record(
            data,
            subscription_id=uuid.uuid4().hex[:16],
            now_iso=datetime.now().isoformat(),
            user_agent=payload.user_agent,
        )
        records.append(record)
        await self._save(db, user_id, records)
        logger.info("用户 %s 新增 Web Push 订阅（共 %d 条）", user_id, len(records))
        return {"created": True, "subscription": _out(record)}

    async def unsubscribe(
        self, db: AsyncSession, user_id: int, payload: WebPushUnsubscribeIn
    ) -> dict:
        """退订：给 ``subscription_id`` / ``endpoint`` 精确退订；都不给则退订全部"""
        records = await self._load(db, user_id)
        if not records:
            return {"removed": 0, "remaining": 0}

        target_id = payload.subscription_id
        target_endpoint = payload.endpoint
        if target_id is None and target_endpoint is None:
            kept: list[dict] = []
        else:
            kept = [
                record
                for record in records
                if not (
                    (target_id is not None and record.get("id") == target_id)
                    or (target_endpoint is not None and record.get("endpoint") == target_endpoint)
                )
            ]
        removed = len(records) - len(kept)
        await self._save(db, user_id, kept)
        if removed:
            logger.info("用户 %s 退订 Web Push（移除 %d，剩余 %d）", user_id, removed, len(kept))
        return {"removed": removed, "remaining": len(kept)}

    async def list_subscriptions(self, db: AsyncSession, user_id: int) -> list[dict]:
        """本人订阅列表（不返回 keys 材料）"""
        records = await self._load(db, user_id)
        return [_out(record) for record in records]

    # ------------------------------------------------------------ 发送
    async def _dispatch(
        self,
        records: list[dict],
        payload: dict,
        config: WebPushConfig,
    ) -> tuple[list[dict], list[dict], int]:
        """向一组订阅真实发送，返回 ``(结果明细, 保留记录, 清理数)``

        失效（HTTP 404/410）的记录被**剔除**（不再保留）；成功 / 其它失败的记录保留并计数。
        """
        results: list[WebPushSendResult] = []
        kept: list[dict] = []
        now_iso = datetime.now().isoformat()
        pruned = 0
        for record in records:
            success, status, error = await asyncio.to_thread(
                push_to_endpoint, record, payload, config
            )
            results.append(
                WebPushSendResult(
                    subscription_id=record.get("id"),
                    endpoint=record.get("endpoint"),
                    success=success,
                    status=status,
                    error=error,
                ).model_dump(mode="json")
            )
            if success:
                record["last_sent_at"] = now_iso
                record["send_count"] = int(record.get("send_count") or 0) + 1
                kept.append(record)
            elif status in EXPIRED_STATUS_CODES:
                # 订阅已失效：剔除
                pruned += 1
            else:
                record["fail_count"] = int(record.get("fail_count") or 0) + 1
                kept.append(record)
        return results, kept, pruned

    async def send_to_user(
        self,
        db: AsyncSession,
        payload: WebPushSendIn,
        *,
        config: Optional[WebPushConfig] = None,
        operator_id: Optional[int] = None,
    ) -> dict:
        """向单用户推送（管理端）。未配置 → 400；用户不存在 → 404；无订阅 → 空结果"""
        config = config or load_web_push_config()
        self._ensure_sendable(config)
        if await db.get(UserModel, payload.user_id) is None:
            raise NotFoundError("用户不存在")

        records = await self._load(db, payload.user_id)
        if not records:
            return WebPushSendResponse(total=0, sent=0, failed=0, pruned=0, results=[]).model_dump(
                mode="json"
            )

        notification = build_payload(
            payload.title,
            payload.body,
            icon=payload.icon,
            badge=payload.badge,
            data=payload.data,
            timestamp=datetime.now().isoformat(),
        )
        results, kept, pruned = await self._dispatch(records, notification, config)
        await self._save(db, payload.user_id, kept)
        sent = sum(1 for item in results if item["success"])
        logger.info(
            "Web Push 单推 user=%s operator=%s sent=%s/%s pruned=%s",
            payload.user_id,
            operator_id,
            sent,
            len(records),
            pruned,
        )
        return WebPushSendResponse(
            total=len(records),
            sent=sent,
            failed=len(results) - sent,
            pruned=pruned,
            results=results,
        ).model_dump(mode="json")

    async def broadcast(
        self,
        db: AsyncSession,
        payload: WebPushBroadcastIn,
        *,
        config: Optional[WebPushConfig] = None,
        operator_id: Optional[int] = None,
    ) -> dict:
        """向**全部已有订阅**的用户广播推送（管理端）。未配置 → 400

        不设「主题」概念：本项目无 topic / 分组表，v2 亦无；如需按主题分流需另建表，暂**如实不做**。
        """
        config = config or load_web_push_config()
        self._ensure_sendable(config)

        per_user = await self._all_by_user(db)
        targets = list(per_user.items())[: payload.max_users]
        notification = build_payload(
            payload.title,
            payload.body,
            icon=payload.icon,
            badge=payload.badge,
            data=payload.data,
            timestamp=datetime.now().isoformat(),
        )

        total = sent = failed = pruned = 0
        per_user_details: list[dict] = []
        for user_id, records in targets:
            results, kept, user_pruned = await self._dispatch(records, notification, config)
            await self._save(db, user_id, kept)
            user_sent = sum(1 for item in results if item["success"])
            total += len(records)
            sent += user_sent
            failed += len(results) - user_sent
            pruned += user_pruned
            per_user_details.append(
                {
                    "user_id": user_id,
                    "total": len(records),
                    "sent": user_sent,
                    "pruned": user_pruned,
                }
            )

        logger.info(
            "Web Push 广播 operator=%s users=%s sent=%s/%s pruned=%s",
            operator_id,
            len(targets),
            sent,
            total,
            pruned,
        )
        return {
            "total_users": len(targets),
            "total": total,
            "sent": sent,
            "failed": failed,
            "pruned": pruned,
            "details": per_user_details,
        }

    # ------------------------------------------------------------ 统计 / 清理
    async def stats(
        self, db: AsyncSession, *, config: Optional[WebPushConfig] = None
    ) -> dict:
        """订阅统计（真实从 ``system_settings`` 聚合）"""
        config = config or load_web_push_config()
        per_user = await self._all_by_user(db)
        summary = summarize_subscriptions(per_user)
        return WebPushStatsOut(
            total_users=summary["total_users"],
            total_subscriptions=summary["total_subscriptions"],
            average_per_user=summary["average_per_user"],
            vapid_configured=config.configured,
            webpush_available=config.webpush_available,
        ).model_dump(mode="json")

    async def cleanup(
        self,
        db: AsyncSession,
        *,
        max_age_days: int = 30,
        dry_run: bool = False,
    ) -> dict:
        """清理过期 / 结构非法的订阅（真实删除，``dry_run`` 时只统计）"""
        per_user = await self._all_by_user(db)
        now = datetime.now()
        removed_ids: list[str] = []
        scanned_subscriptions = 0
        for user_id, records in per_user.items():
            scanned_subscriptions += len(records)
            removable = cleanup_ids(records, now, max_age_days)
            if not removable:
                continue
            removed_ids.extend(removable)
            if not dry_run:
                kept = [record for record in records if str(record.get("id")) not in set(removable)]
                await self._save(db, user_id, kept)
        if not dry_run and removed_ids:
            logger.info("Web Push 清理：移除 %d 条失效 / 过期订阅", len(removed_ids))
        return WebPushCleanupOut(
            scanned_users=len(per_user),
            scanned_subscriptions=scanned_subscriptions,
            removed=len(removed_ids),
            dry_run=dry_run,
            removed_ids=removed_ids,
        ).model_dump(mode="json")

    # ------------------------------------------------------------ VAPID 公钥下发
    def vapid_public_key(self, *, config: Optional[WebPushConfig] = None) -> dict:
        """下发 VAPID 公钥（公开信息）。未配置时 ``configured=False`` 并给出原因，**不编造公钥**"""
        config = config or load_web_push_config()
        return {
            "configured": config.configured,
            "public_key": config.public_key or None,
            "subject": config.subject,
            "webpush_available": config.webpush_available,
            "reason": None if config.configured else config.reason(),
        }


def _parse_records(raw: Any) -> list[dict]:
    """把 ``system_settings.setting_value`` 解析为订阅记录数组（坏数据忽略）"""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("Web Push 订阅不是合法 JSON，按空处理：%s", str(raw)[:80])
        return []
    if not isinstance(parsed, list):
        logger.warning("Web Push 订阅不是数组，按空处理")
        return []
    return [item for item in parsed if isinstance(item, dict)]


#: 单例实例
web_push_service = WebPushService()
