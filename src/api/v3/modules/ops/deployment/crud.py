"""deployment 模块的数据访问层（唯一 DB 访问点）"""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.enterprise import DeploymentLog, DeploymentScript
from src.api.v3.core.base_crud import CRUDBase


class DeploymentScriptCRUD(CRUDBase[DeploymentScript, dict, dict]):
    model = DeploymentScript
    keyword_fields = ("name", "description")
    default_order_by = "id"


class DeploymentLogCRUD(CRUDBase[DeploymentLog, dict, dict]):
    model = DeploymentLog
    keyword_fields = ()
    default_order_by = "id"

    async def remove_by_script(self, db: AsyncSession, script_id: int) -> int:
        """按脚本批量删除执行日志（脚本删除时连带清理，避免 FK 残留），返回删除条数"""
        result = await db.execute(delete(self.model).where(self.model.script_id == script_id))
        await db.commit()
        return int(result.rowcount or 0)


deployment_script_crud = DeploymentScriptCRUD()
deployment_log_crud = DeploymentLogCRUD()
