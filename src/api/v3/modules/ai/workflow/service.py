"""ai.workflow 模块业务逻辑：AI 工作流执行记录（只读 + 治理）"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.ai.workflow.crud import ai_workflow_crud
from src.api.v3.modules.ai.workflow.schema import AIWorkflowOut


def _to_out(row) -> dict:
    return AIWorkflowOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class AIWorkflowService:
    """AI 工作流记录（ai 域）；执行引擎为二期，本模块不做任务派发"""

    async def list_workflows(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        user_id: Optional[int] = None, task_type: Optional[str] = None,
        status: Optional[str] = None, keyword: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await ai_workflow_crud.list(
            db, page=page, page_size=page_size, keyword=keyword,
            filters={"user_id": user_id, "task_type": task_type, "status": status},
        )
        return [_to_out(r) for r in rows], total

    async def delete_workflow(self, db: AsyncSession, workflow_id: int) -> None:
        row = await ai_workflow_crud.get(db, workflow_id)
        if row is None:
            raise NotFoundError("工作流记录不存在")
        await ai_workflow_crud.remove(db, row)


ai_workflow_service = AIWorkflowService()
