# -*- coding: utf-8 -*-
"""P2-3 审计导出测试（纯函数 + 假 DB，不依赖数据库）。

盯住导出这条链路的可验证点：

  1. CSV 带 **UTF-8 BOM**（Excel 打开中文不乱码）且列序固定；
  2. 时间区间与条数上限会被带进查询（不是"导出全表"）；
  3. 字段**显式列举**——模型上新增字段不会顺带泄露；
  4. 文件名与 media_type 与格式匹配（CSV / JSON）。
"""

from datetime import datetime

import pytest

# 显式导入参与关系的模型：SQLAlchemy mapper 在首次访问实体属性时才配置，
# 若只导入 PermissionAuditLog，PermissionGroup 的 relationship 会找不到 User 而报错
# （生产环境由应用启动时的完整模型加载规避，测试进程必须自己保证）。
from shared.models import (  # noqa: F401
    PermissionAuditLog,
    PermissionGroup,
    User,
    UserGroupMember,
)
from src.api.v3.modules.ops.audit.service import COLUMNS, AuditExportService


class _Row:
    def __init__(self, row_id: int, **kwargs) -> None:
        self.id = row_id
        self.created_at = kwargs.get("created_at", datetime(2026, 10, 12, 9, 0, 0))
        self.user_id = kwargs.get("user_id", 1)
        self.action = kwargs.get("action", "update")
        self.resource_type = kwargs.get("resource_type", "article")
        self.resource_id = kwargs.get("resource_id", 42)
        self.ip_address = kwargs.get("ip_address", "10.0.0.1")
        self.details = kwargs.get("details", '{"title": "标题"}')
        # 模型之外的字段：不应被导出
        self.secret_column = "SHOULD-NOT-APPEAR"


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows
        self.last_stmt = None

    async def execute(self, stmt):
        self.last_stmt = stmt
        return _Scalars(self._rows)


@pytest.mark.asyncio
class TestFetch:
    async def test_rows_are_projected_to_explicit_columns(self):
        service = AuditExportService()
        rows = await service.fetch(_FakeDB([_Row(1)]), limit=10)
        assert set(rows[0]) == set(COLUMNS)
        assert "secret_column" not in rows[0], "未登记的模型字段不得进入导出"

    async def test_datetime_is_serialized_to_iso(self):
        service = AuditExportService()
        rows = await service.fetch(_FakeDB([_Row(1)]), limit=10)
        assert rows[0]["created_at"].startswith("2026-10-12T09:00:00")

    async def test_query_carries_limit_and_time_range(self):
        """参数确实进入 SQL（而不是取全表后在 Python 里过滤）。"""
        service = AuditExportService()
        db = _FakeDB([_Row(1)])
        await service.fetch(
            db,
            date_from=datetime(2026, 10, 1),
            date_to=datetime(2026, 10, 31),
            limit=7,
        )
        sql = str(db.last_stmt).lower()
        assert "permission_audit_logs" in sql
        assert "created_at" in sql and ">=" in sql and "<=" in sql
        assert "limit" in sql

    async def test_hard_cap_applies(self):
        service = AuditExportService()
        db = _FakeDB([])
        await service.fetch(db, limit=10 ** 9)
        # SQLAlchemy 把 LIMIT 参数化（``LIMIT :param_1``），所以断言参数值而非 SQL 字面量
        params = db.last_stmt.compile().params
        assert 50000 in params.values(), "超过硬上限时应被截到 MAX_ROWS"


class TestSerialization:
    def _sample(self):
        return [
            {
                "id": 1,
                "created_at": "2026-10-12T09:00:00",
                "user_id": 1,
                "action": "update",
                "resource_type": "article",
                "resource_id": 42,
                "ip_address": "10.0.0.1",
                "details": '{"标题": "中文"}',
            },
            {
                "id": 2,
                "created_at": "2026-10-12T09:05:00",
                "user_id": None,
                "action": "delete",
                "resource_type": "comment",
                "resource_id": None,
                "ip_address": None,
                "details": None,
            },
        ]

    def test_csv_has_bom_and_fixed_header(self):
        service = AuditExportService()
        content = service.to_csv(self._sample())
        assert content.startswith(b"\xef\xbb\xbf"), "CSV 必须带 UTF-8 BOM（Excel 中文不乱码）"
        text = content.decode("utf-8-sig")
        header = text.splitlines()[0]
        assert header.split(",") == list(COLUMNS)

    def test_csv_renders_none_as_empty(self):
        service = AuditExportService()
        text = service.to_csv(self._sample()).decode("utf-8-sig")
        assert "\n2,2026-10-12T09:05:00,,delete" in text, "None 应渲染为空列而不是 'None'"

    def test_json_is_utf8_and_pretty(self):
        service = AuditExportService()
        content = service.to_json(self._sample())
        text = content.decode("utf-8")
        assert '"action": "update"' in text
        assert "中文" in text, "JSON 不应转义中文（ensure_ascii=False）"


@pytest.mark.asyncio
class TestExport:
    async def test_csv_export_metadata(self):
        service = AuditExportService()
        content, media_type, filename = await service.export(_FakeDB([_Row(1)]), fmt="csv", limit=10)
        assert media_type.startswith("text/csv")
        assert filename.startswith("audit-") and filename.endswith(".csv")
        assert content.startswith(b"\xef\xbb\xbf")

    async def test_json_export_metadata(self):
        service = AuditExportService()
        content, media_type, filename = await service.export(_FakeDB([_Row(1)]), fmt="json", limit=10)
        assert media_type.startswith("application/json")
        assert filename.endswith(".json")
        assert content.lstrip().startswith(b"[")

    async def test_empty_result_still_produces_valid_file(self):
        service = AuditExportService()
        content, _, _ = await service.export(_FakeDB([]), fmt="csv", limit=10)
        assert content.decode("utf-8-sig").strip().splitlines() == [",".join(COLUMNS)]
