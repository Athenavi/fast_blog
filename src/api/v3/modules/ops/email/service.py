"""email 模块业务逻辑：邮件服务配置（凭据脱敏）与订阅列表

真实"邮件模板"需要新表（email_templates），二期落地；发送链路复用
``shared/services/notifications/email_service_integration.py``。
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.ops.email.crud import email_config_crud, email_subscription_crud
from src.api.v3.modules.ops.email.schema import EmailConfigCreate, EmailConfigOut, EmailConfigUpdate

SECRET_FIELDS = ("api_key", "smtp_password")


def _config_out(row) -> dict:
    data = EmailConfigOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    for f in SECRET_FIELDS:
        data[f"has_{f}"] = bool(getattr(row, f, None))
    return data


class EmailService:
    """邮件服务管理（ops 域）"""

    async def list_configs(self, db: AsyncSession) -> list[dict]:
        rows, _total = await email_config_crud.list(db, page=1, page_size=100)
        return [_config_out(r) for r in rows]

    async def create_config(self, db: AsyncSession, payload: EmailConfigCreate) -> dict:
        if payload.is_active:
            # 同一时间只允许一个激活配置
            for other in await self._all_rows(db):
                if other.is_active:
                    await email_config_crud.update(db, other, {"is_active": False})
        row = await email_config_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _config_out(row)

    async def update_config(self, db: AsyncSession, config_id: int, payload: EmailConfigUpdate) -> dict:
        row = await email_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("邮件配置不存在")
        data = payload.model_dump(exclude_unset=True)
        if data.get("is_active"):
            for other in await self._all_rows(db):
                if other.id != config_id and other.is_active:
                    await email_config_crud.update(db, other, {"is_active": False})
        updated = await email_config_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _config_out(updated)

    async def delete_config(self, db: AsyncSession, config_id: int) -> None:
        row = await email_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("邮件配置不存在")
        await email_config_crud.remove(db, row)

    async def list_subscriptions(self, db: AsyncSession, *, page: int = 1, page_size: int = 20):
        rows, total = await email_subscription_crud.list(db, page=page, page_size=page_size)
        from src.api.v3.modules.ops.email.schema import EmailSubscriptionOut

        return [
            EmailSubscriptionOut.model_validate(r, from_attributes=True).model_dump(mode="json")
            for r in rows
        ], total

    async def _all_rows(self, db: AsyncSession):
        rows, _ = await email_config_crud.list(db, page=1, page_size=100)
        return rows


email_service = EmailService()
