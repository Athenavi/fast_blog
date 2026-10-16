"""deployment 模块业务逻辑：部署脚本档案与执行日志查看

本期（T5-11 批次 6）只做「档案管理 + 日志查看」：脚本 CRUD、日志分页 / 详情 / 删除。
**脚本执行编排属后续二期**——真实拉起脚本属高危动作（需审批、沙箱与回滚预案），
本模块不提供任何执行入口。

``parameters`` 的序列化边界也收敛在这里：入参对象 → ``json.dumps`` 落库；
出参对象的解析在 ``schema.DeploymentScriptOut`` 的 ``field_validator(mode="before")``。
"""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.ops.deployment.crud import deployment_log_crud, deployment_script_crud
from src.api.v3.modules.ops.deployment.schema import (
    DeploymentLogOut,
    DeploymentScriptCreate,
    DeploymentScriptOut,
    DeploymentScriptUpdate,
)


def _to_script_out(row) -> dict:
    return DeploymentScriptOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _to_log_out(row) -> dict:
    return DeploymentLogOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _dump_parameters(value: Any) -> Optional[str]:
    """入参对象 → 落库 JSON 字符串；None 透传（更新语义为「清空」）"""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


class DeploymentService:
    """部署脚本与执行日志（ops 域）"""

    # ------------------------------------------------------------------ 脚本档案
    async def list_scripts(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        script_type: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await deployment_script_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"script_type": script_type},
        )
        return [_to_script_out(r) for r in rows], total

    async def create_script(
        self, db: AsyncSession, payload: DeploymentScriptCreate, *, created_by: Optional[int] = None
    ) -> dict:
        data = payload.model_dump()
        data["parameters"] = _dump_parameters(data.get("parameters"))
        if created_by is not None:
            data["created_by"] = created_by
        row = await deployment_script_crud.create(
            db, data | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _to_script_out(row)

    async def update_script(
        self, db: AsyncSession, script_id: int, payload: DeploymentScriptUpdate
    ) -> dict:
        row = await deployment_script_crud.get(db, script_id)
        if row is None:
            raise NotFoundError("部署脚本不存在")
        data = payload.model_dump(exclude_unset=True)
        if "parameters" in data:
            data["parameters"] = _dump_parameters(data["parameters"])
        updated = await deployment_script_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _to_script_out(updated)

    async def delete_script(self, db: AsyncSession, script_id: int) -> None:
        row = await deployment_script_crud.get(db, script_id)
        if row is None:
            raise NotFoundError("部署脚本不存在")
        # deployment_logs.script_id 外键指向本表：删脚本前连带清理其执行历史
        await deployment_log_crud.remove_by_script(db, script_id)
        await deployment_script_crud.remove(db, row)

    # ------------------------------------------------------------------ 执行日志
    async def list_logs(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        script_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await deployment_log_crud.list(
            db, page=page, page_size=page_size, filters={"script_id": script_id, "status": status}
        )
        return [_to_log_out(r) for r in rows], total

    async def get_log(self, db: AsyncSession, log_id: int) -> dict:
        row = await deployment_log_crud.get(db, log_id)
        if row is None:
            raise NotFoundError("部署日志不存在")
        return _to_log_out(row)

    async def delete_log(self, db: AsyncSession, log_id: int) -> None:
        row = await deployment_log_crud.get(db, log_id)
        if row is None:
            raise NotFoundError("部署日志不存在")
        await deployment_log_crud.remove(db, row)


deployment_service = DeploymentService()
