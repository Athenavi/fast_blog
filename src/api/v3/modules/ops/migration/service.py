"""migration 模块业务逻辑：数据迁移任务管理

**执行引擎为二期**：本模块管理任务档案（创建/配置/日志/进度查询），并把任务置为
running/cancelled 状态；真实导入器（按 source_platform 实现的抓取-转换-入库）
尚未接入——``start`` 只做状态与时间戳流转，不执行迁移。接入引擎后只需在
``start_task`` 里派发实际导入协程。
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.migration import MigrationTask
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.ops.migration.crud import migration_log_crud, migration_task_crud
from src.api.v3.modules.ops.migration.schema import MigrationTaskCreate, MigrationTaskOut, MigrationTaskUpdate

logger = get_logger("migration")


def _task_out(row: MigrationTask) -> dict:
    data = MigrationTaskOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    raw = getattr(row, "config", None)
    if isinstance(raw, str) and raw:
        try:
            data["config"] = json.loads(raw)
        except json.JSONDecodeError:
            data["config"] = {"raw": raw}
    return data


class MigrationService:
    """迁移任务管理（ops 域）"""

    async def list_tasks(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        keyword: Optional[str] = None, status: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        filters = {"status": status} if status else {}
        rows, total = await migration_task_crud.list(
            db, page=page, page_size=page_size, keyword=keyword, filters=filters
        )
        return [_task_out(r) for r in rows], total

    async def create_task(
        self, db: AsyncSession, payload: MigrationTaskCreate, *, user_id: int
    ) -> dict:
        config = json.dumps(payload.config, ensure_ascii=False) if payload.config else None
        row = await migration_task_crud.create(
            db,
            {
                "task_name": payload.task_name,
                "source_platform": payload.source_platform,
                "status": "pending",
                "config": config,
                "total_items": payload.total_items,
                "created_by": user_id,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )
        return _task_out(row)

    async def update_task(self, db: AsyncSession, task_id: int, payload: MigrationTaskUpdate) -> dict:
        row = await self._task_or_404(db, task_id)
        if row.status == "running":
            raise BadRequestError("任务运行中，请先取消再编辑")
        data = payload.model_dump(exclude_unset=True)
        if "config" in data:
            data["config"] = json.dumps(data["config"], ensure_ascii=False) if data["config"] else None
        updated = await migration_task_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _task_out(updated)

    async def delete_task(self, db: AsyncSession, task_id: int) -> None:
        row = await self._task_or_404(db, task_id)
        if row.status == "running":
            raise BadRequestError("任务运行中，无法删除")
        await migration_task_crud.remove(db, row)

    async def start_task(self, db: AsyncSession, task_id: int) -> dict:
        """置为 running（真实导入执行为二期，见模块 docstring）"""
        row = await self._task_or_404(db, task_id)
        if row.status == "running":
            raise BadRequestError("任务已在运行中")
        updated = await migration_task_crud.update(
            db, row,
            {"status": "running", "started_at": datetime.now(), "updated_at": datetime.now()},
        )
        return _task_out(updated)

    async def cancel_task(self, db: AsyncSession, task_id: int) -> dict:
        row = await self._task_or_404(db, task_id)
        if row.status != "running":
            raise BadRequestError("任务不在运行中")
        updated = await migration_task_crud.update(
            db, row, {"status": "cancelled", "updated_at": datetime.now()}
        )
        return _task_out(updated)

    async def list_logs(
        self, db: AsyncSession, task_id: int, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[dict], int]:
        await self._task_or_404(db, task_id)

        rows, total = await migration_log_crud.list(
            db, page=page, page_size=page_size, filters={"task_id": task_id}
        )
        from src.api.v3.modules.ops.migration.schema import MigrationLogOut

        return [MigrationLogOut.model_validate(r, from_attributes=True).model_dump(mode="json") for r in rows], total

    async def _task_or_404(self, db: AsyncSession, task_id: int) -> MigrationTask:
        row = await migration_task_crud.get(db, task_id)
        if row is None:
            raise NotFoundError("任务不存在")
        return row


migration_service = MigrationService()
