"""migration 模块业务逻辑：数据迁移任务管理 + **真实导入执行**

**执行引擎**（2026-09-21 批次 18 起）：``start_task`` 会真的导入 —— 读 ``config.file_path``
指向的 **WordPress WXR**，逐条转换入库（分类 / 标签 / 文章），日志与进度实时落库。

默认**后台执行**（``asyncio`` 任务 + 自己的 DB session），``wait=True`` 时同步等待；
``cancel_task`` 会让后台循环在下一个取消点停止。落地范围与跳过规则见
``wxr_importer.py``：不支持的 ``post_type``、重复 slug、映射不到的作者都会**写进日志**，
不做静默丢弃，也没有"假装导入成功"的路径。
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.migration import MigrationTask
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.ops.migration.crud import migration_log_crud, migration_task_crud
from src.api.v3.modules.ops.migration.schema import MigrationTaskCreate, MigrationTaskOut, MigrationTaskUpdate
from src.api.v3.modules.ops.migration.wxr_importer import WXRImporter, parse_wxr

logger = get_logger("migration")

#: 已实现的来源平台导入器（其余平台**如实拒绝启动**，不假装导入）
SUPPORTED_IMPORTERS = {"wordpress"}

#: WXR 文件大小上限（避免超大 XML 拖垮进程；也顺带压制 XML 炸弹类风险）
MAX_WXR_BYTES = 64 * 1024 * 1024

#: 正在后台跑的导入任务（task_id -> asyncio.Task）；仅本进程可见
_RUNNING: dict[int, asyncio.Task] = {}
#: 收到取消请求的任务 id（后台循环在下一个取消点停止）
_CANCEL_REQUESTED: set[int] = set()


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
        # 先清日志再删任务：迁移里外键已加 ON DELETE CASCADE，这里显式清理是为了
        # 对**历史数据**（迁移前建的外键）同样安全 —— 批次 18 实测过缺级联会 500。
        logs, _total = await migration_log_crud.list(
            db, page=1, page_size=0, filters={"task_id": task_id}
        )
        for item in logs:
            await migration_log_crud.remove(db, item)
        await migration_task_crud.remove(db, row)

    async def start_task(self, db: AsyncSession, task_id: int, *, wait: bool = False) -> dict:
        """启动导入：**真实执行** WXR 导入（批次 18 起不再是"只流转状态"）

        默认后台执行（立即返回 ``running``，进度与日志可实时查询）；
        ``wait=True`` 时同步等待完成（便于测试与小文件）。

        启动前逐项校验（**不通过就直接报错，不留下"看着在跑"的假任务**）：
        来源平台必须有已实现的导入器、配置里的 ``file_path`` 必须存在且大小合法。
        """
        row = await self._task_or_404(db, task_id)
        if row.status == "running":
            raise BadRequestError("任务已在运行中")

        platform = (row.source_platform or "").strip().lower()
        if platform not in SUPPORTED_IMPORTERS:
            raise BadRequestError(
                f"来源平台「{row.source_platform}」的导入器尚未实现"
                f"（当前支持：{sorted(SUPPORTED_IMPORTERS)}）"
            )

        raw_path = str(self._config(row).get("file_path") or "").strip()
        if not raw_path:
            raise BadRequestError("任务配置缺少 file_path（服务端 WXR 文件路径）")
        path = Path(raw_path)
        if not path.is_file():
            raise BadRequestError(f"WXR 文件不存在：{path}")
        size = path.stat().st_size
        if size <= 0:
            raise BadRequestError(f"WXR 文件为空：{path}")
        if size > MAX_WXR_BYTES:
            raise BadRequestError(f"WXR 文件过大（{size} 字节，上限 {MAX_WXR_BYTES}）")

        now = datetime.now()
        row = await migration_task_crud.update(
            db,
            row,
            {
                "status": "running",
                "progress": 0,
                "migrated_items": 0,
                "error_message": None,
                "started_at": now,
                "completed_at": None,
                "updated_at": now,
            },
        )
        _CANCEL_REQUESTED.discard(task_id)

        if wait:
            await self._run_import(task_id, path)
            # 导入走的是**另一个 session**，这里必须刷新才能拿到最终状态与统计
            await db.refresh(row)
            return _task_out(row)

        _RUNNING[task_id] = asyncio.create_task(self._run_import(task_id, path))
        return _task_out(row)

    async def cancel_task(self, db: AsyncSession, task_id: int) -> dict:
        """请求取消：跑着的后台导入会在**下一个取消点**停下并置 ``cancelled``"""
        row = await self._task_or_404(db, task_id)
        if row.status != "running":
            raise BadRequestError("任务不在运行中")
        if task_id in _RUNNING:
            _CANCEL_REQUESTED.add(task_id)
            return _task_out(row)
        # 没有本进程的后台任务（例如进程重启后残留的 running）→ 直接置 cancelled
        now = datetime.now()
        updated = await migration_task_crud.update(
            db, row, {"status": "cancelled", "completed_at": now, "updated_at": now}
        )
        return _task_out(updated)

    # ------------------------------------------------------------ 导入执行
    @staticmethod
    def _config(row: MigrationTask) -> dict:
        raw = getattr(row, "config", None)
        if isinstance(raw, str) and raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return raw if isinstance(raw, dict) else {}

    async def _run_import(self, task_id: int, path: Path) -> None:
        """后台导入入口：解析 → 逐条导入（日志 / 进度实时落库）→ 收尾

        后台任务**必须用自己的 session**（请求的 session 在响应返回时就关了）。
        """
        from src.utils.database.unified_manager import db_manager

        try:
            feed = parse_wxr(path.read_bytes())
        except Exception as exc:  # noqa: BLE001 - 解析失败同样要落库
            await self._finalize_failed(task_id, f"WXR 解析失败：{exc}")
            _RUNNING.pop(task_id, None)
            return

        try:
            async with db_manager.get_session_no_auto_commit() as db:
                task = await migration_task_crud.get(db, task_id)
                if task is None:
                    return
                # WXR 里作者匹配不到时，用任务创建者兜底（并在日志里说明）
                importer = WXRImporter(default_author_id=task.created_by)

                async def on_progress(stats, new_logs) -> None:
                    for entry in new_logs:
                        await migration_log_crud.create(
                            db,
                            {
                                "task_id": task_id,
                                "log_level": entry.level,
                                "message": entry.message,
                                "item_type": entry.item_type,
                                "item_id": entry.item_id,
                                "created_at": datetime.now(),
                            },
                        )
                    await migration_task_crud.update(
                        db,
                        task,
                        {
                            "total_items": stats.total,
                            "migrated_items": stats.imported,
                            "progress": stats.progress(),
                            "updated_at": datetime.now(),
                        },
                    )

                stats, _logs = await importer.run(
                    db,
                    feed,
                    on_progress=on_progress,
                    should_cancel=lambda: task_id in _CANCEL_REQUESTED,
                )
                cancelled = task_id in _CANCEL_REQUESTED
                finished = datetime.now()
                await migration_task_crud.update(
                    db,
                    task,
                    {
                        "status": "cancelled" if cancelled else "completed",
                        "total_items": stats.total,
                        "migrated_items": stats.imported,
                        "progress": stats.progress(),
                        "completed_at": finished,
                        "updated_at": finished,
                    },
                )
        except Exception as exc:  # noqa: BLE001 - 兜底：未预期异常也要落库而不是静默
            logger.exception("迁移任务执行异常: task_id=%s", task_id)
            await self._finalize_failed(task_id, str(exc))
        finally:
            _RUNNING.pop(task_id, None)
            _CANCEL_REQUESTED.discard(task_id)

    async def _finalize_failed(self, task_id: int, message: str) -> None:
        """把任务与一条错误日志写进库（独立 session，供后台任务使用）"""
        from src.utils.database.unified_manager import db_manager

        try:
            async with db_manager.get_session_no_auto_commit() as db:
                task = await migration_task_crud.get(db, task_id)
                if task is None:
                    return
                now = datetime.now()
                await migration_task_crud.update(
                    db,
                    task,
                    {
                        "status": "failed",
                        "error_message": message[:2000],
                        "completed_at": now,
                        "updated_at": now,
                    },
                )
                await migration_log_crud.create(
                    db,
                    {
                        "task_id": task_id,
                        "log_level": "error",
                        "message": message,
                        "created_at": now,
                    },
                )
        except Exception:  # noqa: BLE001 - 收尾失败只记日志
            logger.exception("迁移任务收尾失败: task_id=%s", task_id)

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
