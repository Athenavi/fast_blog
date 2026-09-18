"""webhook 模块业务逻辑

CRUD 直接操作 ``webhooks`` 表（项目里没有对应的 service 方法）；派发复用
``shared/services/notifications/webhook_service.py::webhook_service.trigger_event``。
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.webhook.webhook import Webhook
from src.api.v3.common.json_field import dump_json_field, parse_json_field
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.ops.webhook.crud import webhook_crud
from src.api.v3.modules.ops.webhook.schema import WebhookCreate, WebhookUpdate

logger = get_logger("webhook")

#: 可订阅事件（v2 引用的 ``WEBHOOK_EVENTS`` 是未定义符号，这里给出权威清单）
WEBHOOK_EVENTS: tuple[str, ...] = (
    "article.created",
    "article.updated",
    "article.published",
    "article.deleted",
    "comment.created",
    "comment.approved",
    "user.registered",
    "user.login",
    "user.logout",
    "media.uploaded",
    "webhook.test",
)


def to_out(webhook: Webhook) -> dict:
    """响应**不含 secret**，只告知是否已配置"""
    events = parse_json_field(webhook.events)
    if isinstance(events, str):
        events = [events]
    return {
        "id": webhook.id,
        "name": webhook.name,
        "url": webhook.url,
        "events": list(events or []),
        "is_active": bool(webhook.is_active),
        "has_secret": bool(webhook.secret),
        "created_at": webhook.created_at,
        "updated_at": webhook.updated_at,
    }


class WebhookOpsService:
    """Webhook 订阅管理"""

    async def list_webhooks(
        self, db: AsyncSession, *, is_active: Optional[bool] = None
    ) -> List[dict]:
        webhooks, _total = await webhook_crud.list(
            db,
            page=1,
            page_size=0,
            filters={"is_active": is_active},
            order_by="id",
            order="asc",
        )
        return [to_out(webhook) for webhook in webhooks]

    async def _get_row(self, db: AsyncSession, webhook_id: int) -> Webhook:
        webhook = await webhook_crud.get(db, webhook_id)
        if webhook is None:
            raise NotFoundError("Webhook 不存在")
        return webhook

    async def get_webhook(self, db: AsyncSession, webhook_id: int) -> dict:
        return to_out(await self._get_row(db, webhook_id))

    async def create_webhook(self, db: AsyncSession, payload: WebhookCreate) -> dict:
        webhook = await webhook_crud.create(
            db,
            {
                "name": payload.name,
                "url": payload.url,
                "events": dump_json_field(payload.events),
                "secret": payload.secret,
                "is_active": payload.is_active,
            },
        )
        return to_out(webhook)

    async def update_webhook(
        self, db: AsyncSession, webhook_id: int, payload: WebhookUpdate
    ) -> dict:
        webhook = await self._get_row(db, webhook_id)
        data = payload.model_dump(exclude_unset=True)
        if "events" in data and data["events"] is not None:
            data["events"] = dump_json_field(data["events"])
        if not data.get("secret"):
            data.pop("secret", None)  # 留空表示不修改

        webhook = await webhook_crud.update(db, webhook, data)
        return to_out(webhook)

    async def delete_webhook(self, db: AsyncSession, webhook_id: int) -> None:
        webhook = await self._get_row(db, webhook_id)
        await webhook_crud.remove(db, webhook)

    async def test_webhook(self, db: AsyncSession, webhook_id: int) -> dict:
        """触发一次测试事件（派发器自身按订阅关系投递）"""
        webhook = await self._get_row(db, webhook_id)
        detail: Optional[str] = None
        try:
            from shared.services.notifications.webhook_service import webhook_service as dispatcher

            # 注意：trigger_event 是 staticmethod(event_name, payload)，**不接受 db 参数**
            # （v2 传 db= 正是其端点 500 的原因之一）
            await dispatcher.trigger_event(
                "webhook.test",
                {
                    "webhook_id": webhook.id,
                    "name": webhook.name,
                    "url": webhook.url,
                    "message": "这是一次测试投递",
                },
            )
        except Exception as exc:  # noqa: BLE001 - 派发失败要让调用方看到原因
            logger.exception("webhook 测试派发失败 id=%s", webhook_id)
            detail = f"{type(exc).__name__}: {exc}"

        return {
            "triggered": detail is None,
            "event": "webhook.test",
            "webhook_id": webhook.id,
            "detail": detail,
        }

    @staticmethod
    def available_events() -> List[dict]:
        return [{"event": name} for name in WEBHOOK_EVENTS]


webhook_ops_service = WebhookOpsService()
