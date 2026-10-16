"""ai.workflow 模块业务逻辑：AI 任务执行（**真实调用模型**，不再是只读台账）

执行链路：请求 → 取 ``AIConfig``（按用户密码派生的密钥解密 api_key）→ 按 ``task_type``
渲染提示词（``tasks.py``）→ 调模型（``../llm.py``，openai 兼容 / anthropic 两套协议）→
把结果写回 ``output_data`` / ``tokens_used`` / ``status``。

**失败也落库**（``status=failed`` + ``error_message``）并把原因抛给调用方：
既不吞错，也不留"看起来成功"的记录。
"""

import json
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.modules.ai import llm
from src.api.v3.modules.ai.config.crud import ai_config_crud
from src.api.v3.modules.ai.config.service import ai_config_service
from src.api.v3.modules.ai.workflow import tasks
from src.api.v3.modules.ai.workflow.crud import ai_workflow_crud
from src.api.v3.modules.ai.workflow.schema import AIWorkflowOut, WorkflowExecute


def _to_out(row) -> dict:
    return AIWorkflowOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class AIWorkflowService:
    """AI 任务执行与记录（ai 域）"""

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

    def task_types(self) -> list[dict]:
        """可用任务类型（前端下拉；与执行引擎读同一份表，不会漂移）"""
        return tasks.catalogue()

    async def delete_workflow(self, db: AsyncSession, workflow_id: int) -> None:
        row = await ai_workflow_crud.get(db, workflow_id)
        if row is None:
            raise NotFoundError("工作流记录不存在")
        await ai_workflow_crud.remove(db, row)

    # ------------------------------------------------------------------ 执行
    async def execute(self, db: AsyncSession, payload: WorkflowExecute) -> dict:
        """真实执行一次任务：先落 ``processing``，结束后落 ``completed``/``failed``"""
        task_type = (payload.task_type or tasks.DEFAULT_TASK_TYPE).strip()
        if task_type not in tasks.TASK_TEMPLATES:
            raise BadRequestError(
                f"未知任务类型：{task_type}（可用：{', '.join(sorted(tasks.TASK_TEMPLATES))}）"
            )

        config = await ai_config_crud.get(db, payload.config_id)
        if config is None:
            raise NotFoundError(f"AI 配置不存在：{payload.config_id}")
        settings = await ai_config_service.resolve_llm_settings(db, payload.config_id)
        system, prompt = tasks.render(
            task_type, input_text=payload.input, target_lang=payload.target_lang or "英文"
        )

        row = await ai_workflow_crud.create(
            db,
            {
                "user_id": payload.user_id or config.user_id,
                "task_type": task_type,
                "input_data": json.dumps(
                    {
                        "config_id": payload.config_id,
                        "input": payload.input,
                        "target_lang": payload.target_lang,
                        "prompt": prompt,
                    },
                    ensure_ascii=False,
                ),
                "model_used": settings.model,
                "tokens_used": 0,
                "status": "processing",
                "created_at": datetime.now(),
            },
        )

        started = time.time()
        try:
            result = await llm.complete(
                settings,
                system=system or None,
                prompt=prompt,
                max_tokens=payload.max_tokens,
            )
        except BadRequestError as exc:
            # 失败也留痕（列表里能看到失败与原因），再把原因抛给调用方
            await ai_workflow_crud.update(
                db,
                row,
                {
                    "status": "failed",
                    "error_message": str(exc),
                    "completed_at": datetime.now(),
                },
            )
            raise

        finished = await self._finish(db, row, result, started)
        return _to_out(finished)

    async def retry(self, db: AsyncSession, workflow_id: int) -> dict:
        """用原输入重跑一次（沿用当时的任务类型与配置）"""
        row = await ai_workflow_crud.get(db, workflow_id)
        if row is None:
            raise NotFoundError("工作流记录不存在")
        try:
            meta = json.loads(row.input_data or "{}")
        except ValueError as exc:
            raise BadRequestError("该记录的输入数据已损坏，无法重跑") from exc
        if not isinstance(meta, dict) or not meta.get("input") or not meta.get("config_id"):
            raise BadRequestError("该记录没有可重跑的输入（缺少 config_id / input）")
        return await self.execute(
            db,
            WorkflowExecute(
                config_id=int(meta["config_id"]),
                task_type=row.task_type or tasks.DEFAULT_TASK_TYPE,
                input=str(meta["input"]),
                user_id=row.user_id,
                target_lang=meta.get("target_lang"),
            ),
        )

    # ------------------------------------------------------------------ 内部
    async def _finish(self, db: AsyncSession, row, result: llm.LLMResult, started: float):
        output = {
            "text": result.text,
            "protocol": result.protocol,
            "model": result.model,
            "latency_ms": int((time.time() - started) * 1000),
            "usage": {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
            },
        }
        return await ai_workflow_crud.update(
            db,
            row,
            {
                "status": "completed",
                "output_data": json.dumps(output, ensure_ascii=False),
                "model_used": result.model or row.model_used,
                "tokens_used": int(result.prompt_tokens) + int(result.completion_tokens),
                "error_message": None,
                "completed_at": datetime.now(),
            },
        )


ai_workflow_service = AIWorkflowService()
