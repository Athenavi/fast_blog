"""ops.upgrade 的**真实升级执行器**（把 ``updater/updater.py`` 的能力整合进 src）

与原 ``updater/updater.py`` 的关键差异（都是刻意的安全修正）：

  1. **只替换代码，绝不碰数据**。路径策略 = 允许清单（``ALLOWED_*``）+ 保护清单
     （``PROTECTED_*``，优先级更高）。旧实现用 ``shutil.move(项目根)`` / ``rmtree(项目根)``
     做"原子替换"，会连 ``media/ uploads/ .env backups/`` 一起动掉 —— 本实现不存在这类路径。
  2. **先备份、按清单回滚**。替换前把"将被覆盖的原文件"复制到
     ``backups/update_backups/<old_ver>_<ts>/``（附 ``manifest.json``）；
     回滚按 manifest **精确还原**（含"原本不存在、本次新增"的文件会被删掉），而不是整目录覆盖。
  3. **不自杀进程**。替换完成后新代码要**重启才生效**：可配置 ``restart_command``
     （system_settings 的 ``upgrade.restart_command``，例如 docker/systemd 重启命令），
     未配置就如实返回"需人工重启"，绝不假装已生效。
  4. **每步留痕**。步骤结果逐条返回；失败即停并**自动回滚**；
     成功/失败/回滚都写 ``logs/update_history.json``（与既有基座同口径）。

包结构：``releases/update_{version}.zip``，内层顶层目录固定为 ``update/``
（与 ``scripts/build_release.py`` 的 ``arcname`` 一致），可选同名 ``.sha256`` 校验文件。
"""

import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zipfile import BadZipFile, ZipFile

from shared.utils.update_history import add_update_history
from shared.utils.version_manager import version_manager
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger

logger = get_logger("ops.upgrade.executor")

#: 更新包内层顶层目录（``build_release.py`` 的 arcname 前缀）
PACKAGE_ROOT = "update"

#: 项目根：version.txt 固定在项目根
PROJECT_ROOT: Path = version_manager.version_file.parent

RELEASES_DIR: Path = PROJECT_ROOT / "releases"
BACKUP_ROOT: Path = PROJECT_ROOT / "backups" / "update_backups"
STAGING_ROOT: Path = PROJECT_ROOT / "storage" / "upgrade_staging"

#: 更新包最小体积（<1KB 视为无效包，与预检口径一致）
MIN_PACKAGE_BYTES = 1024

#: alembic 迁移命令超时（秒）
MIGRATION_TIMEOUT = 600

#: **允许**更新包覆盖的目录前缀（相对项目根，POSIX 风格；与 build_release 的清单对齐，
#: 已剔除被整合/删除的 process_supervisor、updater、update_server）
ALLOWED_PREFIXES: tuple[str, ...] = (
    "src/",
    "shared/",
    "cli/",
    "apps/",
    "config/",
    "scripts/",
    "docs/",
    "static/",
    "alembic_migrations/",
    "frontend/web/src/",
    "frontend/web/i18n/",
    "frontend/web/scripts/",
    "frontend/web/public/",
    "frontend/web/.plugin-pages/",
)

#: **允许**覆盖的根级文件（精确匹配）
ALLOWED_FILES: tuple[str, ...] = (
    "main.py",
    "requirements.txt",
    "version.txt",
    ".env_example",
    "README.md",
    "LICENSE",
    "alembic.ini",
    "pyproject.toml",
    "pytest.ini",
    "Makefile",
    "frontend/web/nuxt.config.ts",
    "frontend/web/package.json",
    "frontend/web/tsconfig.json",
    "frontend/web/README.md",
)

#: **保护**目录前缀：数据、凭据、运行态产物 —— 更新包永远动不了
PROTECTED_DIRS: tuple[str, ...] = (
    ".git/",
    ".venv/",
    ".idea/",
    ".vscode/",
    "media/",
    "uploads/",
    "upload_chunks/",
    "storage/",
    "logs/",
    "backups/",
    "releases/",
    "plugins_data/",
    "themes/",
    "translations/",
    "vendor/",
    "public/",
    "node_modules/",
    "frontend/web/node_modules/",
    "frontend/web/.nuxt/",
    "frontend/web/.output/",
    "frontend/web/test-results/",
    "frontend/web/playwright-report/",
)

#: **保护**文件（精确匹配）：环境与凭据
PROTECTED_FILES: tuple[str, ...] = (
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    "frontend/web/.env",
    "frontend/web/.env.development",
    "frontend/web/.env.production",
    "frontend/web/.env.e2e",
)


def _posix(path: str) -> str:
    return path.replace("\\", "/")


def is_protected(rel_path: str) -> bool:
    """是否命中保护清单（**判定优先级最高**）"""
    rel = _posix(rel_path).lstrip("/")
    if rel in PROTECTED_FILES:
        return True
    if Path(rel).name in PROTECTED_FILES:
        return True
    return any(rel == d.rstrip("/") or rel.startswith(d) for d in PROTECTED_DIRS)


def is_allowed(rel_path: str) -> bool:
    """是否在允许清单内"""
    rel = _posix(rel_path).lstrip("/")
    if rel in ALLOWED_FILES:
        return True
    return any(rel.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def can_replace(rel_path: str) -> bool:
    """最终判定：在允许清单内且不在保护清单内"""
    return is_allowed(rel_path) and not is_protected(rel_path)


@dataclass
class StepResult:
    """一个执行步骤的结果"""

    step: str
    ok: bool
    detail: str = ""


@dataclass
class ExecuteResult:
    """一次执行/回滚的结果"""

    target_version: str
    from_version: str
    ok: bool
    steps: list[StepResult] = field(default_factory=list)
    backup_id: Optional[str] = None
    files_replaced: int = 0
    skipped: int = 0
    need_restart: bool = True
    restart_detail: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_version": self.target_version,
            "from_version": self.from_version,
            "ok": self.ok,
            "backup_id": self.backup_id,
            "files_replaced": self.files_replaced,
            "skipped": self.skipped,
            "need_restart": self.need_restart,
            "restart_detail": self.restart_detail,
            "steps": [
                {"step": item.step, "ok": item.ok, "detail": item.detail} for item in self.steps
            ],
        }


class UpgradeExecutor:
    """升级执行器（真实文件操作；所有 IO 都在 ``to_thread`` 里跑，不阻塞事件循环）"""

    # ------------------------------------------------------------ 路径策略
    @staticmethod
    def path_policy() -> dict[str, list[str]]:
        """给管理端看的"会动什么 / 绝不动什么"清单"""
        return {
            "allowed_prefixes": list(ALLOWED_PREFIXES),
            "allowed_files": list(ALLOWED_FILES),
            "protected_dirs": list(PROTECTED_DIRS),
            "protected_files": list(PROTECTED_FILES),
            "project_root": str(PROJECT_ROOT),
            "releases_dir": str(RELEASES_DIR),
            "backup_root": str(BACKUP_ROOT),
        }

    @staticmethod
    def package_path(target_version: str) -> Path:
        return RELEASES_DIR / f"update_{target_version}.zip"

    # ------------------------------------------------------------ 包校验
    def verify_package(self, target_version: str) -> tuple[bool, str, Optional[Path]]:
        """校验更新包：存在 / 体积 / ZIP 完整性 / 可选 sha256。返回 ``(ok, detail, path)``"""
        package = self.package_path(target_version)
        if not package.is_file():
            return False, f"本地更新包不存在：{package}（请先放入 releases/ 目录）", None
        size = package.stat().st_size
        if size < MIN_PACKAGE_BYTES:
            return False, f"更新包过小（{size} 字节 < {MIN_PACKAGE_BYTES}），疑似无效包", package
        try:
            with ZipFile(package) as zf:
                bad = zf.testzip()
        except BadZipFile as exc:
            return False, f"不是合法的 ZIP：{exc}", package
        if bad:
            return False, f"ZIP 内存在损坏文件：{bad}", package

        sha_file = package.with_suffix(".zip.sha256")
        if sha_file.is_file():
            expected = sha_file.read_text(encoding="utf-8").strip().split()[0]
            actual = _sha256(package)
            if expected.lower() != actual.lower():
                return False, f"sha256 不匹配（期望 {expected[:12]}… 实际 {actual[:12]}…）", package
            return True, f"包校验通过（{size} 字节，sha256 匹配）", package
        return True, f"包校验通过（{size} 字节；未提供 .sha256，未做摘要校验）", package

    def plan(self, target_version: str) -> dict[str, Any]:
        """预演：包里哪些会被替换、哪些被跳过（保护/不在允许清单）"""
        ok, detail, package = self.verify_package(target_version)
        if not ok or package is None:
            raise BadRequestError(detail)

        replace: list[str] = []
        skipped: list[str] = []
        with ZipFile(package) as zf:
            for name in zf.namelist():
                info = zf.getinfo(name)
                if info.is_dir():
                    continue
                rel = self._strip_package_root(name)
                if not rel:
                    continue
                (replace if can_replace(rel) else skipped).append(rel)

        return {
            "target_version": target_version,
            "package": str(package),
            "package_detail": detail,
            "will_replace": sorted(replace),
            "will_replace_count": len(replace),
            "skipped": sorted(skipped),
            "skipped_count": len(skipped),
            "collisions_with_protected": [
                item for item in replace if is_protected(item)
            ],
        }

    @staticmethod
    def _strip_package_root(name: str) -> str:
        """去掉包内顶层 ``update/`` 前缀；不在该前缀下的条目忽略（返回空串）"""
        rel = _posix(name).lstrip("/")
        if rel == PACKAGE_ROOT or rel.startswith(f"{PACKAGE_ROOT}/"):
            return rel[len(PACKAGE_ROOT):].lstrip("/")
        return ""

    # ------------------------------------------------------------ 执行
    async def execute(
        self,
        target_version: str,
        *,
        run_migration: bool = True,
        clear_cache: bool = True,
        restart_command: Optional[str] = None,
    ) -> ExecuteResult:
        import asyncio

        return await asyncio.to_thread(
            self._execute_sync,
            target_version,
            run_migration,
            clear_cache,
            restart_command,
        )

    def _execute_sync(
        self,
        target_version: str,
        run_migration: bool,
        clear_cache: bool,
        restart_command: Optional[str],
    ) -> ExecuteResult:
        from_version = version_manager.get_version()
        result = ExecuteResult(
            target_version=target_version, from_version=from_version, ok=False
        )
        started = time.time()

        ok, detail, package = self.verify_package(target_version)
        result.steps.append(StepResult("verify_package", ok, detail))
        if not ok or package is None:
            self._record(from_version, target_version, "failed", started, detail)
            return result

        plan = self.plan(target_version)
        result.steps.append(
            StepResult(
                "plan",
                plan["will_replace_count"] > 0,
                f"将替换 {plan['will_replace_count']} 个文件、跳过 {plan['skipped_count']} 个"
                f"（保护路径碰撞 {len(plan['collisions_with_protected'])}）",
            )
        )
        if plan["will_replace_count"] == 0:
            self._record(from_version, target_version, "failed", started, "包内没有可替换的文件")
            return result

        staging = STAGING_ROOT / target_version
        try:
            _reset_dir(staging)
            with ZipFile(package) as zf:
                zf.extractall(staging)
        except Exception as exc:  # noqa: BLE001 - 解包失败即失败
            result.steps.append(StepResult("extract", False, f"解包失败：{exc}"))
            self._record(from_version, target_version, "failed", started, str(exc))
            return result
        result.steps.append(StepResult("extract", True, f"已解包到 {staging}"))

        backup_id = f"{from_version}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        backup_dir = BACKUP_ROOT / backup_id
        try:
            entries, replaced = self._apply(staging, target_version, backup_dir, plan)
        except Exception as exc:  # noqa: BLE001 - 替换失败：自动回滚
            result.steps.append(StepResult("apply", False, f"替换失败：{exc}"))
            rollback_detail = self._rollback_sync(backup_id)
            result.steps.append(StepResult("auto_rollback", True, rollback_detail))
            self._record(from_version, target_version, "failed", started, str(exc))
            return result

        result.backup_id = backup_id
        result.files_replaced = replaced
        result.skipped = plan["skipped_count"]
        result.steps.append(
            StepResult("apply", True, f"已替换 {replaced} 个文件；备份 {backup_id}")
        )
        _write_manifest(backup_dir, backup_id, from_version, target_version, entries)

        if run_migration:
            ok, detail = self._run_alembic()
            result.steps.append(StepResult("alembic_upgrade", ok, detail))
            if not ok:
                rollback_detail = self._rollback_sync(backup_id)
                result.steps.append(
                    StepResult("auto_rollback", True, f"迁移失败已回滚：{rollback_detail}")
                )
                self._record(from_version, target_version, "failed", started, detail)
                return result

        if clear_cache:
            result.steps.append(StepResult("clear_cache", True, self._clear_cache()))

        try:
            version_manager.bump_version(target_version)
            result.steps.append(StepResult("bump_version", True, f"version.txt → {target_version}"))
        except Exception as exc:  # noqa: BLE001 - 写版本失败不算致命，但要如实报
            result.steps.append(StepResult("bump_version", False, f"写版本号失败：{exc}"))

        result.ok = True
        result.need_restart = True
        if restart_command:
            ok, detail = self._run_restart(restart_command)
            result.steps.append(StepResult("restart", ok, detail))
            result.restart_detail = detail
            result.need_restart = not ok
        else:
            result.restart_detail = "未配置重启命令：新代码需**重启服务**后生效"
            result.steps.append(StepResult("restart", True, result.restart_detail))

        self._record(from_version, target_version, "success", started, None)
        _reset_dir(staging)
        return result

    # ------------------------------------------------------------ 回滚
    async def rollback(self, backup_id: str) -> dict[str, Any]:
        import asyncio

        return await asyncio.to_thread(self._rollback_sync, backup_id)

    def _rollback_sync(self, backup_id: str) -> str:
        """按 manifest 精确还原；返回说明文字（失败抛异常由调用方处理）"""
        backup_dir = BACKUP_ROOT / backup_id
        manifest_file = backup_dir / "manifest.json"
        if not manifest_file.is_file():
            raise BadRequestError(f"备份不存在或缺少 manifest：{backup_dir}")
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

        restored = 0
        removed = 0
        for entry in manifest.get("entries", []):
            rel = str(entry.get("path") or "")
            if not rel or is_protected(rel):
                continue
            target = PROJECT_ROOT / rel
            if entry.get("existed"):
                source = backup_dir / rel
                if source.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    restored += 1
            elif target.is_file():
                target.unlink()  # 本次新增的文件 → 回滚时删除
                removed += 1

        add_update_history(
            from_version=str(manifest.get("target_version") or ""),
            to_version=str(manifest.get("from_version") or ""),
            status="rolled_back",
            detail=f"按备份 {backup_id} 回滚：还原 {restored} 个、删除 {removed} 个",
        )
        return f"已回滚（还原 {restored} 个文件、删除 {removed} 个新增文件）；备份：{backup_id}"

    # ------------------------------------------------------------ 内部步骤
    def _apply(
        self,
        staging: Path,
        target_version: str,
        backup_dir: Path,
        plan: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], int]:
        """把 staging 里的白名单文件复制到项目根；先备份被覆盖的原文件

        返回 ``(manifest entries, 替换文件数)``。
        """
        root_in_staging = staging / PACKAGE_ROOT
        if not root_in_staging.is_dir():
            raise ValueError(f"包内缺少顶层目录 {PACKAGE_ROOT}/")

        entries: list[dict[str, Any]] = []
        replaced = 0
        for rel in plan["will_replace"]:
            source = root_in_staging / rel
            if not source.is_file():
                continue
            target = PROJECT_ROOT / rel
            existed = target.is_file()
            if existed:
                backup_file = backup_dir / rel
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup_file)
            entries.append(
                {
                    "path": rel,
                    "existed": existed,
                    "size": source.stat().st_size,
                    "target_version": target_version,
                }
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            replaced += 1

        backup_dir.mkdir(parents=True, exist_ok=True)
        return entries, replaced

    @staticmethod
    def _run_alembic() -> tuple[bool, str]:
        """执行 ``alembic upgrade head``（迁移失败视为升级失败，会触发回滚）"""
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=MIGRATION_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return False, f"alembic 迁移超时（>{MIGRATION_TIMEOUT}s）"
        except Exception as exc:  # noqa: BLE001 - 命令无法执行也要如实报
            return False, f"无法执行 alembic：{exc}"
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
            return False, "alembic 迁移失败：" + " / ".join(tail)
        return True, "数据库迁移完成（alembic upgrade head）"

    @staticmethod
    def _clear_cache() -> str:
        """清掉应用缓存目录（保留目录本身；不动 media/uploads/logs）"""
        cache_dir = PROJECT_ROOT / "storage" / "cache"
        if not cache_dir.is_dir():
            return "无 storage/cache 目录，跳过"
        removed = 0
        for item in cache_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                removed += 1
            except OSError:
                continue
        return f"已清理 storage/cache 下 {removed} 项"

    @staticmethod
    def _run_restart(command: str) -> tuple[bool, str]:
        """执行配置的重启命令（真实执行；失败如实返回输出尾巴）"""
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001
            return False, f"重启命令执行失败：{exc}"
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
            return False, "重启命令返回非 0：" + " / ".join(tail)
        return True, "重启命令已执行（请稍后确认服务已恢复）"

    @staticmethod
    def _record(
        from_version: str,
        to_version: str,
        status: str,
        started: float,
        error: Optional[str],
    ) -> None:
        """写升级历史（与既有基座同口径）"""
        try:
            add_update_history(
                from_version=from_version,
                to_version=to_version,
                status=status,
                duration=round(time.time() - started, 2),
                error=error,
            )
        except Exception:  # noqa: BLE001 - 历史写入失败不影响升级结论
            logger.exception("写升级历史失败: %s -> %s", from_version, to_version)

    # ------------------------------------------------------------ 备份列表
    @staticmethod
    def list_backups(limit: int = 20) -> list[dict[str, Any]]:
        """列出本地升级备份（新→旧）"""
        if not BACKUP_ROOT.is_dir():
            return []
        items: list[dict[str, Any]] = []
        for path in BACKUP_ROOT.iterdir():
            if not path.is_dir():
                continue
            manifest_file = path / "manifest.json"
            info: dict[str, Any] = {"backup_id": path.name, "path": str(path)}
            if manifest_file.is_file():
                try:
                    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001 - 坏 manifest 也要列出来
                    manifest = {}
                info.update(
                    {
                        "from_version": manifest.get("from_version"),
                        "target_version": manifest.get("target_version"),
                        "created_at": manifest.get("created_at"),
                        "files": len(manifest.get("entries") or []),
                    }
                )
            items.append(info)
        items.sort(key=lambda item: str(item.get("created_at") or item["backup_id"]), reverse=True)
        return items[: max(1, limit)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _write_manifest(
    backup_dir: Path,
    backup_id: str,
    from_version: str,
    target_version: str,
    entries: list[dict[str, Any]],
) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "manifest.json").write_text(
        json.dumps(
            {
                "backup_id": backup_id,
                "from_version": from_version,
                "target_version": target_version,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "entries": entries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


upgrade_executor = UpgradeExecutor()
