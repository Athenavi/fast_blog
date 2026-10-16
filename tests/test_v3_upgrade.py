"""ops/upgrade（在线升级 / 执行器 / 更新包）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import json
import os
import pytest
import zipfile
from fastapi import FastAPI
from pathlib import Path
from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.ops.upgrade import executor as executor_module
from src.api.v3.modules.ops.upgrade import packages as upgrade_packages
from src.api.v3.modules.ops.upgrade.executor import UpgradeExecutor, can_replace, is_protected
from src.api.v3.modules.ops.upgrade.schema import UpgradeExecutePayload
from src.api.v3.modules.ops.upgrade.service import upgrade_service

# ============================================================ 来自 test_v3_upgrade.py（0 项）
# GET 鉴权断言组只放 GET 路由；check/apply 是 POST 路由（GET 打 POST 路由是 405 不是 401）
AUTH_GET_PATHS = (
    "/api/v3/ops/upgrade/status",
)

AUTH_POST_PATHS = (
    "/api/v3/ops/upgrade/check",
    "/api/v3/ops/upgrade/apply",
)


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ============================================================ 来自 test_v3_upgrade_executor.py（14 项）
# ---------------------------------------------------------------- 路径策略
def test_allowed_code_paths_can_be_replaced():
    for rel in (
            "src/app.py",
            "shared/utils/version_manager.py",
            "cli/commands/upgrade.py",
            "alembic_migrations/versions/x.py",
            "config/models.yaml",
            "frontend/web/src/pages/index.vue",
            "main.py",
            "version.txt",
    ):
        assert can_replace(rel), rel


def test_data_and_secrets_are_never_replaced():
    for rel in (
            ".env",
            ".env.production",
            "frontend/web/.env.e2e",
            "media/2026/photo.jpg",
            "uploads/a.png",
            "storage/cache/x.json",
            "logs/main_app.log",
            "backups/update_backups/x/manifest.json",
            "releases/update_1.0.0.zip",
            "plugins_data/seo/state.json",
            "themes/my-theme/index.html",
            "node_modules/lodash/index.js",
            "frontend/web/.nuxt/manifest.json",
            "frontend/web/.output/server/index.mjs",
    ):
        assert can_replace(rel) is False, rel
        assert is_protected(rel) is True, rel


def test_removed_dirs_are_no_longer_replaceable():
    """被整合/删除的目录（process_supervisor / updater / update_server）不再在允许清单里"""
    for rel in (
            "process_supervisor/process_manager.py",
            "updater/updater.py",
            "update_server/server.py",
    ):
        assert can_replace(rel) is False, rel


def test_package_root_prefix_is_stripped():
    assert UpgradeExecutor._strip_package_root("update/src/app.py") == "src/app.py"
    assert UpgradeExecutor._strip_package_root("update/") == ""
    assert UpgradeExecutor._strip_package_root("src/app.py") == ""
    assert UpgradeExecutor._strip_package_root("other/file.txt") == ""


def test_path_policy_exposes_boundaries():
    policy = UpgradeExecutor.path_policy()

    assert "src/" in policy["allowed_prefixes"]
    assert ".env" in policy["protected_files"]
    assert "media/" in policy["protected_dirs"]
    assert policy["project_root"]


# ---------------------------------------------------------------- 包校验与预演
def _make_package(releases: Path, version: str, entries: dict[str, str]) -> Path:
    releases.mkdir(parents=True, exist_ok=True)
    package = releases / f"update_{version}.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return package


def test_verify_package_reports_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(executor_module, "RELEASES_DIR", tmp_path)
    executor = UpgradeExecutor()

    ok, detail, path = executor.verify_package("9.9.9")
    assert ok is False
    assert "不存在" in detail
    assert path is None


def test_verify_package_rejects_too_small(tmp_path, monkeypatch):
    monkeypatch.setattr(executor_module, "RELEASES_DIR", tmp_path)
    _make_package(tmp_path, "1.0.1", {"update/version.txt": "x"})

    ok, detail, _path = UpgradeExecutor().verify_package("1.0.1")
    assert ok is False
    assert "过小" in detail


def test_plan_separates_replaced_and_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(executor_module, "RELEASES_DIR", tmp_path)
    # 每个文件内容都不同且不可压缩，确保包体超过最小体积门槛
    _make_package(
        tmp_path,
        "1.0.2",
        {
            "update/src/demo.py": os.urandom(4096).hex(),
            "update/main.py": os.urandom(4096).hex(),
            "update/media/evil.jpg": os.urandom(2048).hex(),
            "update/.env": os.urandom(2048).hex(),
            "update/process_supervisor/legacy.py": os.urandom(2048).hex(),
        },
    )

    plan = UpgradeExecutor().plan("1.0.2")

    assert plan["will_replace"] == ["main.py", "src/demo.py"]
    assert set(plan["skipped"]) == {".env", "media/evil.jpg", "process_supervisor/legacy.py"}
    assert plan["collisions_with_protected"] == []


def test_list_backups_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(executor_module, "BACKUP_ROOT", tmp_path / "nope")

    assert UpgradeExecutor.list_backups() == []


# ---------------------------------------------------------------- 执行护栏
@pytest.mark.asyncio
async def test_execute_requires_explicit_confirm():
    payload = UpgradeExecutePayload(target_version="1.0.3", confirm=False)

    with pytest.raises(BadRequestError) as exc:
        await upgrade_service.execute(None, payload)
    assert "confirm=true" in str(exc.value)


@pytest.mark.asyncio
async def test_execute_rejects_illegal_version():
    payload = UpgradeExecutePayload(target_version="1.0.3; rm -rf /", confirm=True)

    with pytest.raises(BadRequestError) as exc:
        await upgrade_service.execute(None, payload)
    assert "非法字符" in str(exc.value)


@pytest.mark.asyncio
async def test_execute_refuses_when_precheck_fails(tmp_path, monkeypatch):
    """包不存在 → 预检不通过 → 直接拒绝（不会走到写文件那一步）

    ``db`` 传 None：这条路径在读取设置之前就返回了，正是我们要保证的"先拦后做"。
    """
    monkeypatch.setattr(executor_module, "RELEASES_DIR", tmp_path)
    payload = UpgradeExecutePayload(target_version="1.0.4", confirm=True)

    with pytest.raises(BadRequestError) as exc:
        await upgrade_service.execute(None, payload)
    assert "预检未通过" in str(exc.value)


@pytest.mark.asyncio
async def test_rollback_requires_confirm():
    from src.api.v3.modules.ops.upgrade.schema import UpgradeRollbackPayload

    with pytest.raises(BadRequestError) as exc:
        await upgrade_service.rollback(UpgradeRollbackPayload(backup_id="x", confirm=False))
    assert "confirm=true" in str(exc.value)


@pytest.mark.asyncio
async def test_plan_requires_target_version():
    with pytest.raises(BadRequestError):
        await upgrade_service.plan("")


# ============================================================ 来自 test_v3_upgrade_packages.py（6 项）
def _write_package(releases: Path, version: str, *, with_metadata: bool = True) -> Path:
    releases.mkdir(parents=True, exist_ok=True)
    package = releases / f"update_{version}.zip"
    package.write_bytes(b"PK\x03\x04" + b"0" * 2048)
    if with_metadata:
        (releases / f"update_{version}.json").write_text(
            json.dumps({"build_time": "2026-09-21T10:00:00", "version": version}),
            encoding="utf-8",
        )
    (releases / f"update_{version}.zip.sha256").write_text("deadbeef\n", encoding="utf-8")
    return package


def test_list_packages_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(upgrade_packages, "RELEASES_DIR", tmp_path / "missing")

    data = upgrade_packages.list_packages()

    assert data["total"] == 0
    assert data["items"] == []


def test_list_packages_reports_metadata_and_order(tmp_path, monkeypatch):
    monkeypatch.setattr(upgrade_packages, "RELEASES_DIR", tmp_path)
    _write_package(tmp_path, "1.0.0")
    _write_package(tmp_path, "1.0.2", with_metadata=False)

    data = upgrade_packages.list_packages()

    assert data["total"] == 2
    # 按版本号倒序（新的在前）
    assert [item["version"] for item in data["items"]] == ["1.0.2", "1.0.0"]
    newest = data["items"][0]
    assert newest["filename"] == "update_1.0.2.zip"
    assert newest["size"] > 0
    assert newest["sha256_file"] is True
    # 没有 .json 元数据的包依然列出，只是 metadata 为空
    assert newest["metadata"] == {}
    assert data["items"][1]["build_time"] == "2026-09-21T10:00:00"


def test_resolve_package_accepts_real_package(tmp_path, monkeypatch):
    monkeypatch.setattr(upgrade_packages, "RELEASES_DIR", tmp_path)
    package = _write_package(tmp_path, "2.0.0")

    assert upgrade_packages.resolve_package("update_2.0.0.zip") == package


@pytest.mark.parametrize(
    "filename",
    [
        "../version.txt",
        "../../.env",
        "update_9.9.9.zip",  # 不存在
        "version.txt",
        ".env",
        "update_1.0.0.tar.gz",
        "/etc/passwd",
    ],
)
def test_resolve_package_rejects_traversal_and_others(tmp_path, monkeypatch, filename):
    monkeypatch.setattr(upgrade_packages, "RELEASES_DIR", tmp_path)
    _write_package(tmp_path, "1.0.0")

    with pytest.raises(BadRequestError):
        upgrade_packages.resolve_package(filename)


def test_resolve_package_strips_directory_components(tmp_path, monkeypatch):
    """``sub/dir/update_1.0.0.zip`` 会被解析成 releases 下的同名文件（丢弃目录成分）"""
    monkeypatch.setattr(upgrade_packages, "RELEASES_DIR", tmp_path)
    package = _write_package(tmp_path, "1.0.0")

    assert upgrade_packages.resolve_package("sub/dir/update_1.0.0.zip") == package


def test_version_summary_shape():
    from shared.utils.version_manager import version_manager

    data = upgrade_packages.version_summary()

    assert data["current_version"] == version_manager.get_version()
    assert set(data) == {"current_version", "release", "database", "author", "backend", "frontend"}
    assert isinstance(data["release"], dict)
