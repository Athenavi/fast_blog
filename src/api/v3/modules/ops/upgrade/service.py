"""upgrade 模块业务逻辑：在线升级管理（状态 / 检查 / 干跑预检 / **真实执行**）

能力基座：``shared/utils/version_manager``（当前版本 + 项目根）、
``shared/utils/auto_update_checker``（远端/本地检查 + 版本比较）、
``shared/utils/update_history``（升级历史）、
``executor.py``（真实替换执行器，2026-09-21 由仓库根 ``updater/`` 整合而来）。
"""

import asyncio
import re
from datetime import datetime, timedelta
from zipfile import ZipFile

from shared.utils.auto_update_checker import auto_update_checker
from shared.utils.update_history import update_history_manager
from shared.utils.version_manager import version_manager
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.ops.upgrade import packages as upgrade_packages
from src.api.v3.modules.ops.upgrade.executor import upgrade_executor
from src.api.v3.modules.ops.upgrade.schema import (
    UpgradeApplyOut,
    UpgradeBackupItem,
    UpgradeCheckItem,
    UpgradeCheckOut,
    UpgradeExecuteOut,
    UpgradeHistoryItem,
    UpgradePackagesOut,
    UpgradePlanOut,
    UpgradeSettingsOut,
    UpgradeStatusOut,
    UpgradeVersionsOut,
)
from src.api.v3.modules.system.setting.service import setting_service

#: /status.history 取最近 10 条（与前端契约一致）
HISTORY_LIMIT = 10

#: 升级后重启命令的 system_settings 键（真实执行）
RESTART_COMMAND_KEY = "upgrade.restart_command"

#: 正在执行的升级（进程内，同一时刻只允许一个）。多 worker 下每 worker 各自持有。
_EXECUTING: dict[str, str] = {}

#: 最近一次执行 / 回滚结果（供 /status 展示；进程内保留）
_LAST_RESULT: dict | None = None

#: 后台升级任务引用（防止被 GC 回收）
_TASKS: set = set()

#: 版本号白名单 —— 与 ``executor.verify_package`` 的校验同口径
_VERSION_RE = re.compile(r"^[A-Za-z0-9._-]+$")

#: 更新包最小体积 —— 与 ``executor`` 的 MIN_PACKAGE_BYTES 同口径（<1KB 视为无效）
_MIN_PACKAGE_BYTES = 1024

#: 项目根目录：version_manager 的 version.txt 固定在 ``<项目根>/version.txt``
PROJECT_ROOT = version_manager.version_file.parent

#: 本地更新包目录 —— 与 ``auto_update_checker`` / ``executor`` 同一处
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
        """升级状态：当前版本 / app_path / 进行中的真实升级 / 最近 10 条历史。"""
        history = [_map_history(record) for record in update_history_manager.get_recent(HISTORY_LIMIT)]
        out = UpgradeStatusOut(
            current_version=version_manager.get_version(),
            app_path=str(PROJECT_ROOT),
            in_progress=bool(_EXECUTING),
            in_progress_target=_EXECUTING.get("target_version"),
            last_result=_LAST_RESULT,
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

        检查项与 ``executor`` 的执行前条件同口径：版本号白名单、与当前版本的关系、
        本地更新包 ``releases/update_{v}.zip`` 是否就绪、ZIP 完整性。
        全部通过（``ready=True``）后即可用 ``POST /execute``（``confirm=true``）真实执行；
        预检不通过的请求会被执行入口直接拒绝。
        """
        target = (target_version or "").strip()
        if not target:
            raise BadRequestError("请指定目标版本号（可先调用 POST /upgrade/check 获取 latest_version）")

        current = version_manager.get_version()
        checks: list[UpgradeCheckItem] = []

        # 1) 版本号格式（executor 执行前会做同样的白名单校验）
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
            # 3) 本地更新包：执行器只认 releases/update_{v}.zip（远端下载由部署侧负责）
            if package.exists():
                checks.append(
                    UpgradeCheckItem(name="package_available", passed=True, detail=f"本地更新包就绪：{package}")
                )
            else:
                checks.append(
                    UpgradeCheckItem(
                        name="package_available",
                        passed=False,
                        detail=(
                            f"releases/update_{target}.zip 不存在；"
                            "请先把更新包放到 releases/ 目录（原 8001 更新服务已并入本模块）"
                        ),
                    )
                )

            # 4) 包完整性：与 executor.verify_package 同口径（>=1KB 且 ZIP testzip 通过）
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

    # ------------------------------------------------------------ 真实升级（批次 18 整合）
    async def path_policy(self) -> dict:
        """路径策略：会动哪些代码路径 / 绝不触碰哪些数据路径（给管理端看清风险）"""
        return upgrade_executor.path_policy()

    # ------------------------------------------------------------ 版本与本地包（原文 update_server）
    async def versions(self) -> dict:
        """版本明细：release / database / author + backend / frontend"""
        data = await asyncio.to_thread(upgrade_packages.version_summary)
        return UpgradeVersionsOut.model_validate(data).model_dump(mode="json")

    async def packages(self) -> dict:
        """本地更新包清单（``releases/update_*.zip`` + 同名元数据）"""
        data = await asyncio.to_thread(upgrade_packages.list_packages)
        return UpgradePackagesOut.model_validate(data).model_dump(mode="json")

    @staticmethod
    def package_file(filename: str):
        """解析待下载的包路径（只允许 ``releases/update_*.zip``，防路径穿越）"""
        return upgrade_packages.resolve_package(filename)

    async def plan(self, target_version: str) -> dict:
        """执行预演：列出将被替换 / 被跳过的文件（只读，不落盘、不改任何文件）"""
        target = (target_version or "").strip()
        if not target:
            raise BadRequestError("请指定目标版本号（可先调用 POST /upgrade/check 获取 latest_version）")
        data = await asyncio.to_thread(upgrade_executor.plan, target)
        return UpgradePlanOut.model_validate(data).model_dump(mode="json")

    async def list_backups(self, limit: int = 20) -> dict:
        items = await asyncio.to_thread(upgrade_executor.list_backups, limit)
        rows = [UpgradeBackupItem.model_validate(item).model_dump(mode="json") for item in items]
        return {"items": rows, "total": len(rows)}

    async def get_settings(self, db) -> dict:
        """读取升级设置（当前只有"重启命令"）"""
        command: str | None = None
        try:
            setting = await setting_service.get_setting(db, RESTART_COMMAND_KEY)
            raw = setting.get("parsed_value")
            if isinstance(raw, str) and raw.strip():
                command = raw.strip()
            elif isinstance(raw, dict):
                value = raw.get("value")
                command = str(value).strip() if value else None
        except Exception:  # noqa: BLE001 - 未配置即 None
            command = None
        return UpgradeSettingsOut(restart_command=command, configured=bool(command)).model_dump(
            mode="json"
        )

    async def save_settings(self, db, payload) -> dict:
        """保存重启命令（**会被真实执行**，因此只允许升级权限持有者设置）"""
        command = (payload.restart_command or "").strip()
        await setting_service.upsert(
            db,
            RESTART_COMMAND_KEY,
            value=command,
            setting_type="string",
            description="升级完成后执行的重启命令（真实执行；留空表示需人工重启）",
            is_public=False,
        )
        return await self.get_settings(db)

    async def execute(self, db, payload, *, wait: bool = False) -> dict:
        """**真实升级**：预检通过后替换代码文件、跑 alembic、清缓存、可选重启

        护栏：
          - 必须显式 ``confirm=true``（写文件操作，防误触）；
          - 同一时刻只允许一个升级在跑；
          - 预检未通过直接拒绝执行；
          - 失败自动回滚（见 ``executor``）。
        """
        if not payload.confirm:
            raise BadRequestError(
                "真实升级会改写代码文件并执行数据库迁移；请在请求里显式传 confirm=true"
            )
        target = (payload.target_version or "").strip()
        if not _VERSION_RE.match(target or ""):
            raise BadRequestError("版本号含非法字符（仅允许字母、数字与 . _ -）")
        if _EXECUTING:
            raise BadRequestError(
                f"已有升级正在执行（目标 {_EXECUTING.get('target_version')}），请等待完成"
            )

        precheck = await self.precheck_apply(target)
        if not precheck.get("ready"):
            failed = [item["name"] for item in precheck["checks"] if not item["passed"]]
            raise BadRequestError(f"预检未通过，拒绝执行：{failed}")

        restart = (await self.get_settings(db)).get("restart_command")
        _EXECUTING["target_version"] = target
        if wait:
            try:
                return await self._run_execute(
                    target, payload.run_migration, payload.clear_cache, restart
                )
            finally:
                _EXECUTING.clear()

        task = asyncio.create_task(
            self._run_execute(target, payload.run_migration, payload.clear_cache, restart)
        )
        _TASKS.add(task)
        task.add_done_callback(_TASKS.discard)
        return {
            "started": True,
            "target_version": target,
            "in_progress": True,
            "need_restart": True,
            "detail": "升级已在后台开始；用 GET /upgrade/status 查看进度与结果",
        }

    async def _run_execute(
        self,
        target: str,
        run_migration: bool,
        clear_cache: bool,
        restart_command: str | None,
    ) -> dict:
        global _LAST_RESULT
        try:
            result = await upgrade_executor.execute(
                target,
                run_migration=run_migration,
                clear_cache=clear_cache,
                restart_command=restart_command,
            )
            data = UpgradeExecuteOut.model_validate(result.to_dict()).model_dump(mode="json")
            _LAST_RESULT = data
            return data
        finally:
            _EXECUTING.clear()

    async def rollback(self, payload) -> dict:
        """按备份回滚代码文件（同样需要 ``confirm=true``）"""
        global _LAST_RESULT
        if not payload.confirm:
            raise BadRequestError("回滚会覆盖当前代码文件；请显式传 confirm=true")
        try:
            detail = await upgrade_executor.rollback(payload.backup_id)
        except BadRequestError:
            raise
        except Exception as exc:  # noqa: BLE001 - 回滚失败要如实报
            raise BadRequestError(f"回滚失败：{exc}") from exc
        data = {
            "dry_run": False,
            "ok": True,
            "from_version": "",
            "target_version": "",
            "need_restart": True,
            "restart_detail": detail,
            "steps": [{"step": "rollback", "ok": True, "detail": detail}],
        }
        _LAST_RESULT = data
        return UpgradeExecuteOut.model_validate(data).model_dump(mode="json")


upgrade_service = UpgradeService()
