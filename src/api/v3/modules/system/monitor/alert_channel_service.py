"""告警推送渠道：把 ``monitoring_alerts`` 真实推送到外部渠道

v3 的 ``system/monitor`` 已有告警 CRUD 与 SLA 计算，但**没有任何对外推送**；
v2 的 ``shared/services/security/security_alert.py``（17.4KB）用 ``AlertChannel`` 抽象做了
email / webhook / sms 三种渠道（其中 sms 只有 TODO，从未实现）。

v3 落在 ``notification_integrations`` 真表上：

  - 渠道类型：``telegram`` / ``discord`` / ``slack`` / ``webhook`` / ``email``
  - ``bot_token`` 落库前 AES-256-GCM 加密（``core/secret_box.py``，读接口只回 ``has_token``）
  - 推送**真实执行**：``httpx`` POST（webhook/discord/slack）、Telegram Bot API、
    邮件走 ``shared/services/notifications/email_service_integration``（SMTP 放线程池，不阻塞事件循环）
  - 推送结果写回 ``monitoring_alerts.notified_users``（JSON 列表：渠道 + 成败 + 摘要 + 时间）

**明确不做**：短信渠道（v2 也只是 TODO，且库里没有短信网关配置表）。
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.integration.notification_integration import NotificationIntegration
from shared.models.monitoring.monitoring_alert import MonitoringAlert
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.secret_box import decrypt_secret, encrypt_secret

logger = get_logger("system.monitor.alert_channel")

#: 支持的推送平台 → 是否需要 webhook_url
PLATFORMS = {
    "telegram": False,
    "discord": True,
    "slack": True,
    "webhook": True,
    "email": False,
}

#: 推送历史在 ``notified_users`` 里最多保留多少条
MAX_HISTORY = 50

#: 单次推送超时（秒）
TIMEOUT_SECONDS = 10.0

DEFAULT_TEMPLATE = "【{severity}】{title}\n{message}\n来源：{source}｜时间：{created_at}"


def render_template(template: Optional[str], alert: MonitoringAlert) -> str:
    """渲染通知模板

    ``notification_template`` 的模型注释写的是 JSON，但实际用途是文本模板：
    因此「JSON 里带 ``text`` / ``template`` 键」与「纯文本模板」两种写法都接受，
    模板变量缺失或格式错误时回退到默认模板（推送不因模板写错而丢）。
    """
    text = (template or "").strip()
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            text = str(parsed.get("text") or parsed.get("template") or "")

    values = {
        "id": alert.id,
        "severity": alert.severity or "info",
        "title": alert.title or "",
        "message": alert.message or "",
        "alert_type": alert.alert_type or "",
        "source": alert.source or "",
        "metric_name": alert.metric_name or "",
        "metric_value": alert.metric_value,
        "threshold": alert.threshold,
        "created_at": alert.created_at.isoformat() if alert.created_at else "",
    }
    for candidate in (text, DEFAULT_TEMPLATE):
        if not candidate:
            continue
        try:
            return candidate.format(**values)[:4000]
        except (KeyError, IndexError, ValueError):
            continue
    return str(values["title"])[:4000]


class AlertChannelService:
    """渠道管理 + 告警分发"""

    # ------------------------------------------------------------------ 渠道
    async def list_channels(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        platform: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        conditions: list[Any] = []
        if platform:
            conditions.append(NotificationIntegration.platform == platform.strip().lower())
        if is_active is not None:
            conditions.append(NotificationIntegration.is_active.is_(bool(is_active)))

        total = int(
            (
                await db.execute(
                    select(func.count()).select_from(NotificationIntegration).where(*conditions)
                )
            ).scalar()
            or 0
        )
        rows = (
            await db.execute(
                select(NotificationIntegration)
                .where(*conditions)
                .order_by(NotificationIntegration.id.desc())
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return [self._channel_out(row) for row in rows], total

    async def create_channel(
        self, db: AsyncSession, payload: Dict[str, Any], *, site_id: Optional[int] = None
    ) -> Dict[str, Any]:
        platform = str(payload.get("platform") or "").strip().lower()
        if platform not in PLATFORMS:
            raise BadRequestError(f"不支持的平台「{platform}」，可选：{sorted(PLATFORMS)}")

        webhook_url = (payload.get("webhook_url") or "").strip()
        bot_token = (payload.get("bot_token") or "").strip()
        channel_id = (payload.get("channel_id") or "").strip()

        if platform == "telegram":
            if not bot_token or not channel_id:
                raise BadRequestError("Telegram 渠道必须提供 bot_token 与 channel_id（chat id）")
        elif platform == "email":
            if not channel_id:
                raise BadRequestError("email 渠道必须提供 channel_id（收件人邮箱）")
        elif PLATFORMS[platform] and not webhook_url:
            raise BadRequestError(f"{platform} 渠道必须提供 webhook_url")

        now = datetime.now()
        row = NotificationIntegration(
            site_id=site_id if site_id is not None else payload.get("site_id"),
            platform=platform,
            webhook_url=webhook_url or None,
            # 落库前加密；读接口只回 has_token，明文永不出网
            bot_token=encrypt_secret(bot_token) if bot_token else None,
            channel_id=channel_id or None,
            enable_new_article_notification=bool(payload.get("enable_new_article_notification", False)),
            enable_comment_notification=bool(payload.get("enable_comment_notification", False)),
            enable_system_alert=bool(payload.get("enable_system_alert", True)),
            notification_template=payload.get("notification_template"),
            is_active=bool(payload.get("is_active", True)),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info("新建告警渠道 id=%s platform=%s", row.id, platform)
        return self._channel_out(row)

    async def update_channel(
        self, db: AsyncSession, channel_id: int, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        row = await self._row_or_404(db, channel_id)
        if payload.get("platform") is not None:
            platform = str(payload["platform"]).strip().lower()
            if platform not in PLATFORMS:
                raise BadRequestError(f"不支持的平台「{platform}」，可选：{sorted(PLATFORMS)}")
            row.platform = platform
        if payload.get("webhook_url") is not None:
            row.webhook_url = (payload["webhook_url"] or "").strip() or None
        if payload.get("bot_token") is not None:
            token = (payload["bot_token"] or "").strip()
            # 留空表示保持原值（与 ops/cdn、ops/backup 的密钥约定一致）
            if token:
                row.bot_token = encrypt_secret(token)
        if payload.get("channel_id") is not None:
            row.channel_id = (payload["channel_id"] or "").strip() or None
        for flag in (
                "enable_new_article_notification",
                "enable_comment_notification",
                "enable_system_alert",
                "is_active",
        ):
            if payload.get(flag) is not None:
                setattr(row, flag, bool(payload[flag]))
        if payload.get("notification_template") is not None:
            row.notification_template = payload["notification_template"] or None

        self._assert_required_fields(row)
        row.updated_at = datetime.now()
        await db.commit()
        await db.refresh(row)
        return self._channel_out(row)

    async def delete_channel(self, db: AsyncSession, channel_id: int) -> None:
        row = await self._row_or_404(db, channel_id)
        await db.delete(row)
        await db.commit()

    async def test_channel(self, db: AsyncSession, channel_id: int) -> Dict[str, Any]:
        """真实发一条测试消息（不经过告警，直接用渠道配置）"""
        row = await self._row_or_404(db, channel_id)
        fake = MonitoringAlert(
            id=0,
            alert_type="channel_test",
            severity="info",
            title="告警渠道测试",
            message="这是一条来自管理端的渠道连通性测试消息。",
            source="system/monitor",
        )
        success, status_code, detail = await self._send(db, row, fake)
        return {
            "channel_id": int(row.id),
            "platform": row.platform,
            "sent": success,
            "status_code": status_code,
            "detail": detail,
        }

    # ------------------------------------------------------------------ 分发
    async def dispatch_alert(
        self, db: AsyncSession, alert_id: int, *, force: bool = False
    ) -> Dict[str, Any]:
        """把告警推送到所有「启用系统告警」的渠道

        ``force=True`` 时忽略 ``enable_system_alert``（手工补发用）。
        """
        alert = await db.get(MonitoringAlert, alert_id)
        if alert is None:
            raise NotFoundError("告警不存在")

        channels = (
            await db.execute(
                select(NotificationIntegration).where(NotificationIntegration.is_active.is_(True))
            )
        ).scalars().all()
        targets = [row for row in channels if force or bool(row.enable_system_alert)]
        if not targets:
            return {
                "alert_id": alert_id,
                "channels": 0,
                "sent": 0,
                "failed": 0,
                "results": [],
                "detail": "没有可用的告警渠道（需 is_active 且 enable_system_alert）",
            }

        results: list[dict[str, Any]] = []
        for row in targets:
            success, status_code, detail = await self._send(db, row, alert)
            results.append(
                {
                    "channel_id": int(row.id),
                    "platform": row.platform,
                    "sent": success,
                    "status_code": status_code,
                    "detail": detail,
                }
            )

        history = self._load_history(alert)
        now = datetime.now()
        history.extend(
            {
                "channel_id": item["channel_id"],
                "platform": item["platform"],
                "sent": item["sent"],
                "status_code": item["status_code"],
                "detail": item["detail"],
                "at": now.isoformat(),
            }
            for item in results
        )
        alert.notified_users = json.dumps(history[-MAX_HISTORY:], ensure_ascii=False)
        alert.updated_at = now
        await db.commit()

        sent = sum(1 for item in results if item["sent"])
        logger.info("告警 %s 推送完成：成功 %s / 失败 %s", alert_id, sent, len(results) - sent)
        return {
            "alert_id": alert_id,
            "channels": len(results),
            "sent": sent,
            "failed": len(results) - sent,
            "results": results,
        }

    async def deliveries(self, db: AsyncSession, alert_id: int) -> Dict[str, Any]:
        """读取该告警的推送历史（来自 ``notified_users``）"""
        alert = await db.get(MonitoringAlert, alert_id)
        if alert is None:
            raise NotFoundError("告警不存在")
        history = self._load_history(alert)
        return {
            "alert_id": alert_id,
            "total": len(history),
            "sent": sum(1 for item in history if item.get("sent")),
            "items": history,
        }

    # ------------------------------------------------------------------ 发送
    async def _send(
        self, db: AsyncSession, channel: NotificationIntegration, alert: MonitoringAlert
    ) -> Tuple[bool, Optional[int], str]:
        """真实发送；返回 ``(成功, HTTP 状态码, 说明)``"""
        platform = (channel.platform or "").lower()
        text = render_template(channel.notification_template, alert)
        try:
            if platform == "telegram":
                return await self._send_telegram(channel, text)
            if platform in ("discord", "slack", "webhook"):
                return await self._send_webhook(channel, platform, alert, text)
            if platform == "email":
                return await self._send_email(db, channel, alert, text)
            return False, None, f"不支持的平台「{platform}」"
        except Exception as exc:  # noqa: BLE001 - 发送失败要如实回给调用方
            logger.warning("渠道 %s 推送失败：%s", channel.id, exc)
            return False, None, f"{type(exc).__name__}: {exc}"

    @staticmethod
    async def _send_telegram(
        channel: NotificationIntegration, text: str
    ) -> Tuple[bool, Optional[int], str]:
        token = decrypt_secret(channel.bot_token or "")
        if not token:
            return False, None, "bot_token 缺失或无法解密"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                url, json={"chat_id": channel.channel_id, "text": text, "disable_web_page_preview": True}
            )
        return response.is_success, response.status_code, response.text[:500]

    @staticmethod
    async def _send_webhook(
        channel: NotificationIntegration,
        platform: str,
        alert: MonitoringAlert,
        text: str,
    ) -> Tuple[bool, Optional[int], str]:
        if not channel.webhook_url:
            return False, None, "webhook_url 缺失"
        if platform == "discord":
            body: Dict[str, Any] = {"content": text}
        elif platform == "slack":
            body = {"text": text}
        else:
            body = {
                "event": "monitor.alert",
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "source": alert.source,
                "metric_name": alert.metric_name,
                "metric_value": float(alert.metric_value) if alert.metric_value is not None else None,
                "threshold": float(alert.threshold) if alert.threshold is not None else None,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            }
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(channel.webhook_url, json=body)
        return response.is_success, response.status_code, response.text[:500]

    @staticmethod
    async def _send_email(
        db: AsyncSession,
        channel: NotificationIntegration,
        alert: MonitoringAlert,
        text: str,
    ) -> Tuple[bool, Optional[int], str]:
        """邮件渠道：复用既有的邮件服务集成（SMTP 走线程池）"""
        from shared.services.notifications.email_service_integration import email_service_integration

        if not channel.channel_id:
            return False, None, "email 渠道缺少收件人（channel_id）"
        config = await email_service_integration.get_config(db)
        if config is None:
            return False, None, "未配置邮件服务（email_service_configs 里没有启用中的配置）"

        html = "<p>" + text.replace("\n", "<br/>") + "</p>"
        ok = await email_service_integration.send_email(
            config,
            channel.channel_id,
            f"[告警] {alert.title or '系统告警'}",
            html,
            text,
        )
        return bool(ok), None, "已交给邮件服务发送" if ok else "邮件服务发送失败（详见服务端日志）"

    # ------------------------------------------------------------------ 内部
    def _assert_required_fields(self, row: NotificationIntegration) -> None:
        platform = (row.platform or "").lower()
        if platform == "telegram" and (not row.bot_token or not row.channel_id):
            raise BadRequestError("Telegram 渠道必须提供 bot_token 与 channel_id（chat id）")
        if platform == "email" and not row.channel_id:
            raise BadRequestError("email 渠道必须提供 channel_id（收件人邮箱）")
        if platform in ("discord", "slack", "webhook") and not row.webhook_url:
            raise BadRequestError(f"{platform} 渠道必须提供 webhook_url")

    @staticmethod
    def _load_history(alert: MonitoringAlert) -> List[Dict[str, Any]]:
        raw = alert.notified_users
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except ValueError:
            return []
        return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []

    async def _row_or_404(self, db: AsyncSession, channel_id: int) -> NotificationIntegration:
        row = await db.get(NotificationIntegration, channel_id)
        if row is None:
            raise NotFoundError("告警渠道不存在")
        return row

    @staticmethod
    def _channel_out(row: NotificationIntegration) -> Dict[str, Any]:
        return {
            "id": row.id,
            "site_id": row.site_id,
            "platform": row.platform,
            "webhook_url": row.webhook_url,
            "channel_id": row.channel_id,
            # 凭据只回「有没有」，明文与密文都不出网
            "has_token": bool(row.bot_token),
            "enable_new_article_notification": bool(row.enable_new_article_notification),
            "enable_comment_notification": bool(row.enable_comment_notification),
            "enable_system_alert": bool(row.enable_system_alert),
            "notification_template": row.notification_template,
            "is_active": bool(row.is_active),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


alert_channel_service = AlertChannelService()
