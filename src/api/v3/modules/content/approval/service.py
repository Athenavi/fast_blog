"""approval 模块业务逻辑：内容审批流（多级记录 + 步骤）

状态约定（``approval_records.status``）：pending 待审 / approved 已通过 / rejected 已驳回。
通过最后一级时记录置 approved 并写 ``completed_at``；任一级驳回则整单 rejected。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.collaboration import ApprovalRecord, ApprovalStep
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.content.approval.crud import approval_record_crud, approval_step_crud
from src.api.v3.modules.content.approval.schema import (
    ApprovalDecisionRequest,
    ApprovalRecordCreate,
    ApprovalRecordOut,
    ApprovalStepOut,
)

logger = get_logger("approval")


def _record_out(row: ApprovalRecord) -> dict:
    return ApprovalRecordOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _step_out(row: ApprovalStep) -> dict:
    return ApprovalStepOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class ApprovalService:
    """内容审批流（content 域）"""

    async def list_records(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        content_type: Optional[str] = None, status: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        filters = {}
        if content_type:
            filters["content_type"] = content_type
        if status:
            filters["status"] = status
        rows, total = await approval_record_crud.list(
            db, page=page, page_size=page_size, filters=filters
        )
        return [_record_out(r) for r in rows], total

    async def create_record(
        self, db: AsyncSession, payload: ApprovalRecordCreate, *, applicant_id: int
    ) -> dict:
        row = await approval_record_crud.create(
            db,
            {
                "content_type": payload.content_type,
                "content_id": payload.content_id,
                "applicant_id": applicant_id,
                "current_level": 1,
                "max_level": payload.max_level,
                "status": "pending",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )
        logger.info("审批单创建 type=%s content=%s record=%s", payload.content_type, payload.content_id, row.id)
        return _record_out(row)

    async def get_record_with_steps(self, db: AsyncSession, record_id: int) -> dict:
        record = await approval_record_crud.get(db, record_id)
        if record is None:
            raise NotFoundError("审批单不存在")
        steps = (await db.execute(
            select(ApprovalStep).where(ApprovalStep.record_id == record_id).order_by(ApprovalStep.level)
        )).scalars().all()
        data = _record_out(record)
        data["steps"] = [_step_out(s) for s in steps]
        return data

    async def decide(
        self, db: AsyncSession, record_id: int, payload: ApprovalDecisionRequest, *, approver_id: int
    ) -> dict:
        record = await approval_record_crud.get(db, record_id)
        if record is None:
            raise NotFoundError("审批单不存在")
        if record.status != "pending":
            raise BadRequestError("该审批单已结束")

        now = datetime.now()
        db.add(ApprovalStep(
            record_id=record_id,
            level=record.current_level,
            approver_id=approver_id,
            action=payload.action,
            comment=payload.comment,
            reviewed_at=now,
            created_at=now,
        ))

        if payload.action == "reject":
            record.status = "rejected"
            record.completed_at = now
        elif record.current_level >= record.max_level:
            record.status = "approved"
            record.completed_at = now
        else:
            record.current_level += 1
        record.updated_at = now
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info("审批决定 record=%s action=%s by=%s", record_id, payload.action, approver_id)
        return _record_out(record)

    async def delete_record(self, db: AsyncSession, record_id: int) -> None:
        record = await approval_record_crud.get(db, record_id)
        if record is None:
            raise NotFoundError("审批单不存在")
        steps = (await db.execute(
            select(ApprovalStep).where(ApprovalStep.record_id == record_id)
        )).scalars().all()
        for s in steps:
            await approval_step_crud.remove(db, s)
        await approval_record_crud.remove(db, record)


approval_service = ApprovalService()
