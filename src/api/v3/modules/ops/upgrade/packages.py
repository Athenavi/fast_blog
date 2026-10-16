"""ops.upgrade 的本地更新包清单与版本明细（原 ``update_server/`` 的独有能力，已并入）

``update_server``（8001）2026-09-21 批次 18 并入主应用后，它**唯一不重复**的几项能力搬到这里：

  - 本地更新包清单（``releases/update_*.zip`` + 同名 ``.json`` 元数据）；
  - 更新包下载（**只允许** ``releases/`` 下的 ``update_*.zip``，按文件名解析以防路径穿越）；
  - 版本明细（release / database / author + backend / frontend）。

原先由 8001 提供的版本信息、健康检查、更新检查、应用更新、备份管理在 v3 侧本就有对应端点
（``/ops/upgrade/*``、``/system/health``、``/ops/backup/*``），因此不再重复实现。
"""

import json
from pathlib import Path
from typing import Any, Optional

from shared.utils.version_manager import version_manager
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger

logger = get_logger("ops.upgrade.packages")

#: 项目根（与 service/executor 同口径）
PROJECT_ROOT: Path = version_manager.version_file.parent

#: 本地更新包目录
RELEASES_DIR: Path = PROJECT_ROOT / "releases"

#: 允许下载的文件名前缀 / 后缀
PACKAGE_PREFIX = "update_"
PACKAGE_SUFFIX = ".zip"


def version_summary() -> dict[str, Any]:
    """版本明细：release / database / author + backend / frontend（全部来自基座）"""
    all_versions = version_manager.get_all_versions()
    return {
        "current_version": version_manager.get_version(),
        "release": version_manager.get_release_info(),
        "database": version_manager.get_database_info(),
        "author": version_manager.get_author_info(),
        "backend": all_versions.get("BACKEND", {}),
        "frontend": all_versions.get("FRONTEND", {}),
    }


def list_packages() -> dict[str, Any]:
    """列出 ``releases/`` 下的本地更新包（新→旧），带同名 ``.json`` 元数据"""
    items: list[dict[str, Any]] = []
    if RELEASES_DIR.is_dir():
        for package in RELEASES_DIR.glob(f"{PACKAGE_PREFIX}*{PACKAGE_SUFFIX}"):
            metadata: dict[str, Any] = {}
            metadata_file = package.with_suffix(".json")
            if metadata_file.is_file():
                try:
                    loaded = json.loads(metadata_file.read_text(encoding="utf-8"))
                    metadata = loaded if isinstance(loaded, dict) else {}
                except Exception:  # noqa: BLE001 - 元数据坏了不影响列出包
                    metadata = {}
            stat = package.stat()
            items.append(
                {
                    "filename": package.name,
                    "version": package.stem[len(PACKAGE_PREFIX):],
                    "size": stat.st_size,
                    "modified_at": _iso(stat.st_mtime),
                    "build_time": metadata.get("build_time"),
                    "sha256_file": (
                        package.with_suffix(".zip.sha256").is_file()
                    ),
                    "metadata": metadata,
                }
            )
    items.sort(key=lambda item: str(item.get("version") or ""), reverse=True)
    return {"items": items, "total": len(items), "releases_dir": str(RELEASES_DIR)}


def resolve_package(filename: str) -> Path:
    """把请求里的文件名解析成 releases 下的真实路径（**防路径穿越**）

    只接受 ``update_*.zip`` 形式；任何目录成分都被丢弃后再校验。
    """
    name = Path(filename or "").name
    if not name.startswith(PACKAGE_PREFIX) or not name.endswith(PACKAGE_SUFFIX):
        raise BadRequestError("只允许下载 releases/ 下的 update_*.zip")
    path = RELEASES_DIR / name
    if not path.is_file():
        raise BadRequestError(f"更新包不存在：{name}")
    return path


def _iso(timestamp: float) -> Optional[str]:
    from datetime import datetime

    try:
        return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        return None
