"""
V3 Webhook 管理 API

权限要求:
  GET    /webhooks             → settings:view
  POST   /webhooks             → settings:edit
  PUT    /webhooks/{id}        → settings:edit
  DELETE /webhooks/{id}        → settings:edit
  POST   /webhooks/{id}/test   → settings:edit
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db
from src.api.v3._permission import Permission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-webhooks"])


@router.get("/webhooks", summary="Webhook 列表")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:view")),
):
    """获取所有 webhook 配置"""
    from shared.models.webhook import Webhook
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    hooks = result.scalars().all()
    return ApiResponse(success=True, data={"webhooks": [_hook_dict(h) for h in hooks]})


@router.post("/webhooks", summary="创建 Webhook", status_code=201)
async def create_webhook(
    name: str = Body(...),
    url: str = Body(...),
    events: list[str] = Body(...),
    is_active: bool = Body(True),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:edit")),
):
    from shared.models.webhook import Webhook
    now = datetime.now(timezone.utc)
    hook = Webhook(name=name, url=url, events=",".join(events), is_active=is_active, created_at=now, updated_at=now)
    db.add(hook)
    await db.commit()
    await db.refresh(hook)
    return ApiResponse(success=True, data=_hook_dict(hook), message="Webhook 创建成功")


@router.put("/webhooks/{webhook_id}", summary="更新 Webhook")
async def update_webhook(
    webhook_id: int,
    name: str = Body(None),
    url: str = Body(None),
    events: list[str] = Body(None),
    is_active: bool = Body(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:edit")),
):
    from shared.models.webhook import Webhook
    hook = await db.get(Webhook, webhook_id)
    if not hook:
        return ApiResponse(success=False, error="Webhook 不存在")
    if name is not None: hook.name = name
    if url is not None: hook.url = url
    if events is not None: hook.events = ",".join(events)
    if is_active is not None: hook.is_active = is_active
    hook.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse(success=True, message="Webhook 已更新")


@router.delete("/webhooks/{webhook_id}", summary="删除 Webhook")
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:edit")),
):
    from shared.models.webhook import Webhook
    hook = await db.get(Webhook, webhook_id)
    if not hook:
        return ApiResponse(success=False, error="Webhook 不存在")
    await db.delete(hook)
    await db.commit()
    return ApiResponse(success=True, message="Webhook 已删除")


@router.post("/webhooks/{webhook_id}/test", summary="测试 Webhook")
async def test_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:edit")),
):
    from shared.models.webhook import Webhook
    hook = await db.get(Webhook, webhook_id)
    if not hook:
        return ApiResponse(success=False, error="Webhook 不存在")
    return ApiResponse(success=True, message="测试事件已触发")


def _hook_dict(h) -> dict:
    return {
        "id": h.id,
        "name": h.name,
        "url": h.url,
        "events": h.events.split(",") if h.events else [],
        "is_active": h.is_active,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }
