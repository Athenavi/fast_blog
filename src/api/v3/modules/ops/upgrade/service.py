"""upgrade 模块业务逻辑：在线升级管理（状态 / 检查 / 干跑预检）

能力基座：``shared/utils/version_manager``（当前版本 + 项目根）、
``shared/utils/auto_update_checker``（远端/本地检查 + 版本比较）、
``shared/utils/update_history``（升级历史）。
真实替换执行器 ``updater/updater.py`` 本期不由 API 触发（取舍见包 docstring）。
"""

import asyncio
import os
import re
from datetime import datetime, timedelta
from zipfile import ZipFile

from shared.utils.auto_update_checker import auto_update_checker
from shared.utils.update_history import update_history_manager
from shared.utils.version_manager import version_manager
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.ops.upgrade.schema import (
    UpgradeApplyOut,
    UpgradeCheckItem,
    UpgradeCheckOut,
    UpgradeHistoryItem,
    UpgradeStatusOut,
)

#: /status.history 取最近 10 条（与前端契约一致）
HISTORY_LIMIT = 10

#: 版本号白名单 —— 与 ``updater.download_update_package`` 的校验同口径
_VERSION_RE = re.compile(r"^[A-Za-z0-9._-]+$")

#: 更新包最小体积 —— 与 ``updater.verify_package_integrity`` 同口径（<1KB 视为无效）
_MIN_PACKAGE_BYTES = 1024

#: 项目根目录：version_manager 的 version.txt 固定在 ``<项目根>/version.txt``
PROJECT_ROOT = version_manager.version_file.parent

#: 本地更新包目录 —— 与 ``updater``（base_dir/releases）及 ``auto_update_checker`` 同一处
RELEASES_DIR = PROJECT_ROOT / "releases"


def _map_history(record: dict) -> UpgradeHistoryItem:
    """把 update_history 记录映射为契约字段。

    基座记录只有收尾时刻的 ``timestamp`` 与 ``duration``：``finished_at=timestamp``，
    ``started_at=timestamp-duration``（缺 duration 时回退为 finished_at）；
    ``message`` 取失败/回滚记录的 ``error``，成功记录为 null。
    """
    finished = str(record.get("timestamp") or "")
    started = finished
    duration = record.get("duration")
    if finished and isinstance(duration, (int, float)) and duration >= 0:
        try:
            started = (datetime.fromisoformat(finished) - timedelta(seconds=duration)).isoformat(
                timespec="seconds"
            )
        except ValueError:
            started = finished
    error = record.get("error")
    return UpgradeHistoryItem(
        target_version=str(record.get("to_version") or ""),
        status=str(record.get("status") or ""),
        started_at=started,
        finished_at=finished,
        message=str(error) if error else None,
    )


class UpgradeService:
    """在线升级（ops 域，无表）"""

    async def status(self) -> dict:
        """升级状态：当前版本 / app_path / 最近 10 条历史。"""
        history = [_map_history(record) for record in update_history_manager.get_recent(HISTORY_LIMIT)]
        out = UpgradeStatusOut(
            current_version=version_manager.get_version(),
            app_path=str(PROJECT_ROOT),
            # 真实替换本期为人工动作，不存在 API 触发的进行中升级（二期接入后台编排后驱动）
            in_progress=False,
            history=history,
        )
        return out.model_dump(mode="json")

    async def check(self) -> dict:
        """检查更新：远端（GitHub Releases）优先，远端不可达回退本地 releases。

        任何网络 / 扫描异常都吞掉并结构化返回（source="none"），绝不向上抛。
        """
        current = version_manager.get_version()
        remote: dict | None = None
        local: str | None = None
        try:
            remote, local = await asyncio.gather(
                auto_update_checker.check_github_releases(),
                auto_update_checker.check_local_releases(),
            )
        except Exception:  # noqa: BLE001 - 检查失败必须结构化返回
            remote, local = None, None

        if remote and remote.get("version"):
            latest = str(remote["version"])
            has_update = auto_update_checker.compare_versions(current, latest)
            detail = f"远端最新版本 {latest}"
            detail += "，发现可升级的新版本" if has_update else "，当前已是最新版本"
            out = UpgradeCheckOut(
                current_version=current,
                latest_version=latest,
                has_update=has_update,
                source="remote",
                detail=detail,
            )
        elif local:
            has_update = auto_update_checker.compare_versions(current, local)
            detail = f"远端不可达，本地 releases 存在更新包 update_{local}.zip"
            detail += "，可升级" if has_update else "（不高于当前版本）"
            out = UpgradeCheckOut(
                current_version=current,
                latest_version=local,
                has_update=has_update,
                source="local_releases",
                detail=detail,
            )
        else:
            out = UpgradeCheckOut(
                current_version=current,
                latest_version=None,
                has_update=False,
                source="none",
                detail="远端不可达，且本地 releases/ 目录没有更新包",
            )
        return out.model_dump(mode="json")

    async def precheck_apply(self, target_version: str) -> dict:
        """升级干跑预检（POST /apply）：只体检、不替换。

        检查项与 ``updater`` 的执行前条件同口径：版本号白名单、与当前版本的
        关系、本地更新包 ``releases/update_{v}.zip`` 是否就绪、ZIP 完整性。
        全部通过（ready=True）后由人工择时执行
        ``python -m updater.updater --target-version <v> --app-path <项目根>``。
        """
        target = (target_version or "").strip()
        if not target:
            raise BadRequestError("请指定目标版本号（可先调用 POST /upgrade/check 获取 latest_version）")

        current = version_manager.get_version()
        checks: list[UpgradeCheckItem] = []

        # 1) 版本号格式（updater 下载前会做同样的白名单校验）
        format_ok = bool(_VERSION_RE.match(target))
        checks.append(
            UpgradeCheckItem(
                name="version_format",
                passed=format_ok,
                detail="版本号格式合法" if format_ok else "版本号含非法字符（仅允许字母、数字与 . _ -）",
            )
        )

        # 2) 与当前版本的关系：相同版本无需升级；更低版本视为回滚场景（放行但提示）
        if not format_ok:
            checks.append(
                UpgradeCheckItem(name="version_differs", passed=False, detail="版本号格式非法，跳过版本比较")
            )
        elif target == current:
            checks.append(
                UpgradeCheckItem(
                    name="version_differs",
                    passed=False,
                    detail=f"目标版本与当前版本相同（{current}），无需升级",
                )
            )
        else:
            is_newer = auto_update_checker.compare_versions(current, target)
            relation = "发现更高的目标版本" if is_newer else "目标低于当前版本，属回滚场景"
            checks.append(
                UpgradeCheckItem(
                    name="version_differs",
                    passed=True,
                    detail=f"当前 {current} → 目标 {target}（{relation}）",
                )
            )

        package = RELEASES_DIR / f"update_{target}.zip"
        if not format_ok:
            checks.append(
                UpgradeCheckItem(name="package_available", passed=False, detail="版本号格式非法，跳过更新包检查")
            )
            checks.append(
                UpgradeCheckItem(name="package_integrity", passed=False, detail="版本号格式非法，跳过完整性校验"))
        else:
            # 3) 本地更新包：updater 优先取 releases/update_{v}.zip，缺包时执行阶段才会尝试远端下载
            if package.exists():
                checks.append(
                    UpgradeCheckItem(name="package_available", passed=True, detail=f"本地更新包就绪：{package}")
                )
            else:
                server = os.getenv("UPDATE_SERVER_URL", "http://localhost:8001")
                checks.append(
                    UpgradeCheckItem(
                        name="package_available",
                        passed=False,
                        detail=f"releases/update_{target}.zip 不存在；真实替换时将尝试从更新服务器下载（{server}）",
                    )
                )

            # 4) 包完整性：与 updater.verify_package_integrity 同口径（>=1KB 且 ZIP testzip 通过）
            if not package.exists():
                checks.append(UpgradeCheckItem(name="package_integrity", passed=False, detail="无本地包可校验"))
            else:
                try:
                    if package.stat().st_size < _MIN_PACKAGE_BYTES:
                        raise ValueError("更新包文件过小（<1KB），疑似无效包")
                    with ZipFile(package) as zf:
                        bad_file = zf.testzip()
                    if bad_file:
                        raise ValueError(f"ZIP 内存在损坏文件：{bad_file}")
                    checks.append(UpgradeCheckItem(name="package_integrity", passed=True, detail="ZIP 完整性校验通过"))
                except Exception as exc:  # noqa: BLE001 - 校验失败进 checks，不抛
                    checks.append(
                        UpgradeCheckItem(name="package_integrity", passed=False, detail=f"完整性校验失败：{exc}")
                    )

        out = UpgradeApplyOut(dry_run=True, ready=all(item.passed for item in checks), checks=checks)
        return out.model_dump(mode="json")


upgrade_service = UpgradeService()
