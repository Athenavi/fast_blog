"""install 模块业务逻辑：环境自检

**刻意不走 `DBSession` 依赖** —— 否则数据库不通时这个端点自己会 500，
而"数据库不通"恰恰是它最该如实汇报的情况。因此这里自己 try 连接。

检查项：

  - **数据库**：能否执行 ``SELECT 1``（失败只报异常类型名）；
  - **迁移**：DB 里的 ``alembic_version`` 与 alembic 脚本目录的 head 是否一致，
    不一致说明"有迁移没跑"；
  - **是否已安装**：是否存在超级管理员（本项目没有独立的 install 标记表，
    超管存在即视为已安装）；
  - **实时协同依赖**：``pycrdt`` 是否可用（缺失只影响协同编辑）。
"""

from typing import Optional

from sqlalchemy import func, select, text

from src.api.v3.core.logger import get_logger

logger = get_logger("system.install")


def _alembic_head() -> Optional[str]:
    """读 alembic 脚本目录的 head（**不连数据库**）"""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        return ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    except Exception as exc:  # noqa: BLE001 - 缺失 alembic.ini 时应如实降级
        logger.warning("读取 alembic head 失败: %s", exc)
        return None


def _realtime_available() -> bool:
    try:
        import pycrdt  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


class InstallService:
    """安装状态自检"""

    async def status(self) -> dict:
        database: dict = {"ok": False, "error": None}
        migration: dict = {"current": None, "head": _alembic_head(), "up_to_date": False}
        has_superuser = False

        try:
            from shared.models.user import User
            from src.utils.database.unified_manager import db_manager

            async with db_manager.get_session() as db:
                await db.execute(text("SELECT 1"))
                database["ok"] = True
                migration["current"] = (
                    await db.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar()
                has_superuser = (
                    int(
                        (
                            await db.execute(
                                select(func.count())
                                .select_from(User)
                                .where(User.is_superuser.is_(True))
                            )
                        ).scalar()
                        or 0
                    )
                    > 0
                )
        except Exception as exc:  # noqa: BLE001 - 这里就是要兜住所有异常
            database["error"] = type(exc).__name__
            logger.warning("安装自检：数据库检查失败（%s）", type(exc).__name__)

        migration["up_to_date"] = bool(
            migration["current"] and migration["head"] and migration["current"] == migration["head"]
        )

        return {
            "database": database,
            "migration": migration,
            "has_superuser": has_superuser,
            "installed": has_superuser,
            "realtime_available": _realtime_available(),
        }


install_service = InstallService()
