"""审计哈希链与脱敏的回归测试"""
from datetime import datetime

import pytest

from shared.services.security.audit_log_service import AuditLogService
from shared.utils import audit_chain


def _hash(prev, **overrides):
    payload = {
        "user_id": 1,
        "user_name": "admin",
        "action": "update",
        "level": "info",
        "resource_type": "system.user",
        "resource_id": 7,
        "description": "PUT /api/v3/system/user/7",
        "ip_address": "203.0.113.9",
        "before_data": '{"nickname":"old"}',
        "after_data": '{"nickname":"new"}',
        "created_at": datetime(2026, 10, 14, 12, 0, 0),
    }
    payload.update(overrides)
    return audit_chain.compute_entry_hash(prev, **payload)


class TestRedact:
    def test_masks_sensitive_keys_but_keeps_them(self):
        data = {"username": "admin", "password": "s3cret", "api_key": "k"}
        out = audit_chain.redact(data)
        assert out["username"] == "admin"
        assert out["password"] == audit_chain.REDACTED
        assert out["api_key"] == audit_chain.REDACTED
        # 键仍在，保留"这里有过这个字段"的事实
        assert set(out) == {"username", "password", "api_key"}

    def test_masks_nested_structures(self):
        data = {"profile": {"token": "abc", "name": "n"}, "items": [{"secret": "s"}]}
        out = audit_chain.redact(data)
        assert out["profile"]["token"] == audit_chain.REDACTED
        assert out["profile"]["name"] == "n"
        assert out["items"][0]["secret"] == audit_chain.REDACTED


class TestDumpSnapshot:
    def test_none_stays_none(self):
        assert audit_chain.dump_snapshot(None) is None

    def test_dict_is_redacted_and_canonical(self):
        out = audit_chain.dump_snapshot({"b": 1, "a": 2, "password": "x"})
        assert '"a":2' in out and '"b":1' in out
        assert "x" not in out.replace(audit_chain.REDACTED, "")

    def test_json_string_is_parsed_first(self):
        out = audit_chain.dump_snapshot('{"password":"x","n":1}')
        assert audit_chain.REDACTED in out

    def test_plain_string_passes_through(self):
        assert audit_chain.dump_snapshot("not json") == "not json"


class TestComputeEntryHash:
    def test_deterministic(self):
        assert _hash(None) == _hash(None)

    def test_depends_on_prev(self):
        assert _hash(None) != _hash("a" * 64)

    def test_changes_when_content_changes(self):
        assert _hash(None) != _hash(None, action="delete")

    def test_genesis_placeholder_used_when_prev_missing(self):
        # prev 为 None 与显式 GENESIS 应等价（同一个起点）
        assert _hash(None) == _hash(audit_chain.GENESIS)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    """只实现 verify_chain 用到的那一步 execute()"""

    def __init__(self, rows):
        self._rows = rows

    async def execute(self, *_args, **_kwargs):
        return _FakeResult(self._rows)


def _row(prev, **overrides):
    from shared.models.system.audit_log import AuditLog

    log = AuditLog(
        id=overrides.pop("id", 1),
        user_id=1,
        user_name="admin",
        action="update",
        level="info",
        resource_type="system.user",
        resource_id=7,
        description="PUT /api/v3/system/user/7",
        ip_address="203.0.113.9",
        before_data='{"nickname":"old"}',
        after_data='{"nickname":"new"}',
        created_at=datetime(2026, 10, 14, 12, 0, 0),
        prev_hash=prev,
    )
    for key, value in overrides.items():
        setattr(log, key, value)
    log.entry_hash = _hash(prev, **{k: v for k, v in overrides.items() if k != "id"})
    return log


@pytest.mark.asyncio
async def test_verify_chain_accepts_intact_chain():
    first = _row(None, id=1)
    second = _row(first.entry_hash, id=2)
    service = AuditLogService()

    result = await service.verify_chain(_FakeDB([first, second]))

    assert result["valid"] is True
    assert result["checked"] == 2


@pytest.mark.asyncio
async def test_verify_chain_detects_modified_row():
    first = _row(None, id=1)
    second = _row(first.entry_hash, id=2)
    second.user_name = "attacker"  # 篡改内容，不改 entry_hash

    result = await AuditLogService().verify_chain(_FakeDB([first, second]))

    assert result["valid"] is False
    assert result["broken_at_id"] == 2
    assert "被修改" in result["reason"]


@pytest.mark.asyncio
async def test_verify_chain_detects_deleted_row():
    first = _row(None, id=1)
    second = _row(first.entry_hash, id=2)
    third = _row(second.entry_hash, id=3)

    # 删掉中间那条后，第三条的 prev_hash 与现存前驱对不上
    result = await AuditLogService().verify_chain(_FakeDB([first, third]))

    assert result["valid"] is False
    assert result["broken_at_id"] == 3


@pytest.mark.asyncio
async def test_verify_chain_empty_table_is_valid():
    result = await AuditLogService().verify_chain(_FakeDB([]))
    assert result["valid"] is True
    assert result["checked"] == 0


@pytest.mark.asyncio
async def test_verify_chain_allows_trimmed_history():
    """保留策略删掉了最早记录时，现存第一条的 prev_hash 允许悬空"""
    survivor = _row("d" * 64, id=99)  # prev 指向已被清理的行
    result = await AuditLogService().verify_chain(_FakeDB([survivor]))
    assert result["valid"] is True
    assert result["checked"] == 1
