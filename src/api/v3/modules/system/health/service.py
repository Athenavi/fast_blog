"""health 模块的业务逻辑

不依赖任何业务模型，只提供探针所需的信息；
``ready`` 探针会真实执行一次 ``SELECT 1`` 以确认数据库可用。
"""

import os
import tomllib
from pathlib import Path
from typing import Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.logger import get_logger

logger = get_logger("health")

SERVICE_NAME = "fastblog-api-v3"


def _project_root() -> Path:
    """向上找到含 version.txt 的项目根目录"""
    for parent in Path(__file__).resolve().parents:
        if (parent / "version.txt").exists():
            return parent
    return Path.cwd()


def _read_version() -> str:
    """读取版本号

    ``version.txt`` 是 TOML（``[RELEASE] version = ...``），若被改成纯文本也能兜底。
    """
    try:
        raw = (_project_root() / "version.txt").read_bytes()
    except OSError:
        return "unknown"

    try:
        data = tomllib.loads(raw.decode("utf-8"))
        version = (data.get("RELEASE") or {}).get("version")
        if version:
            return str(version)
    except Exception:  # noqa: BLE001 - 非 TOML 时按纯文本兜底
        pass

    text_content = raw.decode("utf-8", "ignore").strip()
    return text_content.splitlines()[0] if text_content else "unknown"


class HealthService:
    """健康探针服务"""

    service_name = SERVICE_NAME

    def build_payload(self) -> dict:
        """构造不含依赖检查的基础载荷（live 探针使用）"""
        return {
            "status": "ok",
            "service": self.service_name,
            "version": _read_version(),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "checks": {},
        }

    async def probe_database(self, db: AsyncSession) -> Tuple[bool, str]:
        """探测数据库连通性，返回 ``(是否可用, 描述)``"""
        try:
            await db.execute(text("SELECT 1"))
            return True, "ok"
        except Exception as exc:  # noqa: BLE001 - 探针不能把异常抛给调用方
            logger.error("数据库探针失败：%s", exc)
            return False, f"unavailable: {type(exc).__name__}"


health_service = HealthService()
