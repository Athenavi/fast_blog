"""Test: AuthPermission（权限控制依赖）与权限码规范化

盯住权限重构 P0/P1 的核心行为：

  1. **规范化不做 `:` ↔ `.` 转换**（P0-1 的根因就是那个转换 —— 这是回归测试）
  2. superuser 放行，且不触发权限码加载（唯一 bypass 点）
  3. 未声明权限码 = 仅需认证
  4. 通配 `*` / `*:*:*` 放行
  5. **ANY 语义**（任一命中即通过），与官方 `AuthPermission` 一致
  6. 无权限 → `ForbiddenError`
  7. 加载失败（Redis/DB 异常）→ `ForbiddenError`（fail-closed，绝不放行）
"""

import pytest

from src.api.v3.core.exceptions import ForbiddenError
from src.api.v3.core.permission.constants import normalize_code
from src.api.v3.core.permission.control import AuthPermission

LOAD_PATCH_TARGET = "src.api.v3.core.permission.control.load_codes"


class FakeUser:
    def __init__(self, user_id: int = 1, is_superuser: bool = False) -> None:
        self.id = user_id
        self.is_superuser = is_superuser


def _loader_returning(codes: set[str]):
    async def _load(db, user_id, request=None):  # noqa: ANN001, ARG001
        return frozenset(codes)

    return _load


def _loader_raising():
    async def _load(db, user_id, request=None):  # noqa: ANN001, ARG001
        raise RuntimeError("redis/db down")

    return _load


def _loader_must_not_be_called():
    async def _load(db, user_id, request=None):  # noqa: ANN001, ARG001
        raise AssertionError("该路径不应触发权限码加载")

    return _load


# ------------------------------------------------------------------ 规范化
def test_normalize_code_does_not_convert_separators():
    """回归：绝不把冒号转成点号（旧实现据此比较，导致权限校验恒失败）"""
    assert normalize_code("article:view") == "article:view"
    assert normalize_code(" module_system:user:query ") == "module_system:user:query"
    # 点号形式原样保留（不转换），由数据层保证与 capabilities.code 一致
    assert normalize_code("article.view") == "article.view"


def test_normalize_code_rejects_empty_and_blank_segment():
    with pytest.raises(ValueError):
        normalize_code("")
    with pytest.raises(ValueError):
        normalize_code("   ")
    with pytest.raises(ValueError):
        normalize_code("article::view")


# ------------------------------------------------------------------ 控制依赖
@pytest.mark.asyncio
async def test_superuser_bypass_skips_loading(monkeypatch):
    monkeypatch.setattr(LOAD_PATCH_TARGET, _loader_must_not_be_called())
    permission = AuthPermission("article:view")

    user = await permission(None, FakeUser(is_superuser=True), None)  # type: ignore[arg-type]

    assert user.is_superuser is True


@pytest.mark.asyncio
async def test_no_codes_means_authentication_only(monkeypatch):
    monkeypatch.setattr(LOAD_PATCH_TARGET, _loader_must_not_be_called())
    permission = AuthPermission()

    user = await permission(None, FakeUser(), None)  # type: ignore[arg-type]

    assert user.id == 1


@pytest.mark.asyncio
async def test_any_semantics_passes_when_one_matches(monkeypatch):
    """ANY 语义：任一权限码命中即通过（官方语义）"""
    monkeypatch.setattr(LOAD_PATCH_TARGET, _loader_returning({"article:view"}))
    permission = AuthPermission("article:delete", "article:view")

    user = await permission(None, FakeUser(), None)  # type: ignore[arg-type]

    assert user.id == 1


@pytest.mark.asyncio
async def test_missing_permission_raises_forbidden(monkeypatch):
    monkeypatch.setattr(LOAD_PATCH_TARGET, _loader_returning({"article:view"}))
    permission = AuthPermission("article:delete")

    with pytest.raises(ForbiddenError):
        await permission(None, FakeUser(), None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_no_permissions_at_all_raises_forbidden(monkeypatch):
    monkeypatch.setattr(LOAD_PATCH_TARGET, _loader_returning(set()))
    permission = AuthPermission("article:view")

    with pytest.raises(ForbiddenError):
        await permission(None, FakeUser(), None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_wildcard_on_user_side_passes(monkeypatch):
    monkeypatch.setattr(LOAD_PATCH_TARGET, _loader_returning({"*:*:*"}))
    permission = AuthPermission("module_content:article:publish")

    user = await permission(None, FakeUser(), None)  # type: ignore[arg-type]

    assert user.id == 1


@pytest.mark.asyncio
async def test_wildcard_on_request_side_passes(monkeypatch):
    monkeypatch.setattr(LOAD_PATCH_TARGET, _loader_must_not_be_called())
    permission = AuthPermission("*")

    user = await permission(None, FakeUser(), None)  # type: ignore[arg-type]

    assert user.id == 1


@pytest.mark.asyncio
async def test_loader_failure_is_fail_closed(monkeypatch):
    """缓存/DB 异常时必须拒绝，绝不因故障放行"""
    monkeypatch.setattr(LOAD_PATCH_TARGET, _loader_raising())
    permission = AuthPermission("article:view")

    with pytest.raises(ForbiddenError):
        await permission(None, FakeUser(), None)  # type: ignore[arg-type]


def test_auth_control_requires_at_least_one_code():
    """便捷工厂必须显式给出权限码（避免误写成"仅认证"）"""
    from src.api.v3.core.deps import AuthControl

    with pytest.raises(ValueError):
        AuthControl()
