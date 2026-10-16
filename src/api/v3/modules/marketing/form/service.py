"""form 模块业务逻辑：表单构建器（表单 / 字段 / 提交）"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.form import Form, FormField
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.marketing.form.crud import form_crud, form_field_crud, form_submission_crud
from src.api.v3.modules.marketing.form.schema import (
    FormCreate,
    FormFieldCreate,
    FormFieldOut,
    FormFieldUpdate,
    FormOut,
    FormPublicSubmitRequest,
    FormSubmissionOut,
    FormUpdate,
)

logger = get_logger("form")


def _form_out(row: Form) -> dict:
    return FormOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _field_out(row: FormField) -> dict:
    return FormFieldOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _submission_out(row) -> dict:
    data = FormSubmissionOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    raw = getattr(row, "data", None)
    if isinstance(raw, str) and raw:
        try:
            data["data"] = json.loads(raw)
        except json.JSONDecodeError:
            data["data"] = {"raw": raw}
    return data


class FormService:
    """表单构建器（marketing 域）"""

    # ------------------------------------------------------------ 表单
    async def list_forms(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, keyword: Optional[str] = None
    ) -> tuple[list[dict], int]:
        rows, total = await form_crud.list(db, page=page, page_size=page_size, keyword=keyword)
        return [_form_out(r) for r in rows], total

    async def create_form(self, db: AsyncSession, payload: FormCreate, *, user_id: int) -> dict:
        if await form_crud.exists(db, slug=payload.slug):
            raise ConflictError(f"表单标识已存在: {payload.slug}")
        row = await form_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _form_out(row)

    async def update_form(self, db: AsyncSession, form_id: int, payload: FormUpdate) -> dict:
        row = await form_crud.get(db, form_id)
        if row is None:
            raise NotFoundError("表单不存在")
        updated = await form_crud.update(
            db, row, payload.model_dump(exclude_unset=True) | {"updated_at": datetime.now()}
        )
        return _form_out(updated)

    async def delete_form(self, db: AsyncSession, form_id: int) -> None:
        row = await form_crud.get(db, form_id)
        if row is None:
            raise NotFoundError("表单不存在")
        # 级联清理字段与提交（无 FK 约束依赖，按归属显式删）
        fields = (await db.execute(select(FormField).where(FormField.form_id == form_id))).scalars().all()
        for f in fields:
            await form_field_crud.remove(db, f)
        from shared.models.form import FormSubmission

        subs = (await db.execute(
            select(FormSubmission).where(FormSubmission.form_id == form_id)
        )).scalars().all()
        for s in subs:
            await form_submission_crud.remove(db, s)
        await form_crud.remove(db, row)

    # ------------------------------------------------------------ 字段
    async def list_fields(self, db: AsyncSession, form_id: int) -> list[dict]:
        await self._form_or_404(db, form_id)
        rows = (await db.execute(
            select(FormField)
            .where(FormField.form_id == form_id)
            .order_by(FormField.order_index, FormField.id)
        )).scalars().all()
        return [_field_out(r) for r in rows]

    async def create_field(self, db: AsyncSession, form_id: int, payload: FormFieldCreate) -> dict:
        await self._form_or_404(db, form_id)
        row = await form_field_crud.create(
            db,
            payload.model_dump() | {"form_id": form_id,
                                    "created_at": datetime.now(), "updated_at": datetime.now()},
        )
        return _field_out(row)

    async def update_field(self, db: AsyncSession, field_id: int, payload: FormFieldUpdate) -> dict:
        row = await form_field_crud.get(db, field_id)
        if row is None:
            raise NotFoundError("字段不存在")
        updated = await form_field_crud.update(
            db, row, payload.model_dump(exclude_unset=True) | {"updated_at": datetime.now()}
        )
        return _field_out(updated)

    async def delete_field(self, db: AsyncSession, field_id: int) -> None:
        row = await form_field_crud.get(db, field_id)
        if row is None:
            raise NotFoundError("字段不存在")
        await form_field_crud.remove(db, row)

    # ------------------------------------------------------------ 提交
    async def list_submissions(
        self, db: AsyncSession, *, form_id: Optional[int] = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[dict], int]:
        filters = {"form_id": form_id} if form_id is not None else {}
        rows, total = await form_submission_crud.list(db, page=page, page_size=page_size, filters=filters)
        return [_submission_out(r) for r in rows], total

    async def delete_submission(self, db: AsyncSession, submission_id: int) -> None:
        row = await form_submission_crud.get(db, submission_id)
        if row is None:
            raise NotFoundError("提交不存在")
        await form_submission_crud.remove(db, row)

    async def public_submit(
        self, db: AsyncSession, slug: str, payload: FormPublicSubmitRequest, *, ip: str, user_agent: str
    ) -> dict:
        """前台匿名提交：按字段定义做必填校验，store_submissions=false 时只回执不落库"""
        form = (await db.execute(select(Form).where(Form.slug == slug))).scalar_one_or_none()
        if form is None or form.status != "published":
            raise NotFoundError("表单不存在或未开放")
        fields = (await db.execute(
            select(FormField).where(FormField.form_id == form.id, FormField.is_active.is_(True))
        )).scalars().all()

        data = payload.data
        for f in fields:
            value = data.get(f.label)
            if f.required and (value is None or str(value).strip() == ""):
                raise BadRequestError(f"必填项未填写: {f.label}")

        if not form.store_submissions:
            return {"accepted": True, "stored": False}

        row = await form_submission_crud.create(
            db,
            {
                "form_id": form.id,
                "data": json.dumps(data, ensure_ascii=False),
                "ip_address": ip,
                "user_agent": user_agent,
                "status": "new",
                "created_at": datetime.now(),
            },
        )
        logger.info("表单提交 form=%s submission=%s", form.id, row.id)
        return {"accepted": True, "stored": True, "submission_id": row.id}

    async def _form_or_404(self, db: AsyncSession, form_id: int) -> Form:
        row = await form_crud.get(db, form_id)
        if row is None:
            raise NotFoundError("表单不存在")
        return row


form_service = FormService()
