# -*- coding: utf-8 -*-
"""P1-3 遗留补齐：字段值（``custom_fields``，EAV）的读写。

钉住：

  1. 写入**必须**按类型定义校验（未定义 key / 必填缺失 / 类型不符 → 400，不静默丢弃）；
  2. 已有值走 **upsert**（更新而不新增）；
  3. 读取**按定义补齐**未填字段为 ``None``（前端表单好渲染）；
  4. 类型不存在或该类型没定义字段时，给出明确错误而不是静默 no-op。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.modules.content.custom_post_type.service import custom_post_type_service

CRUD_GET = "src.api.v3.modules.content.custom_post_type.service.custom_post_type_crud.get"


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeDB:
    """最小假会话：记录 add/commit，execute 返回预置行。"""

    def __init__(self, rows=None):
        self._rows = rows or []
        self.added = []
        self.add = MagicMock(side_effect=self.added.append)
        self.commit = AsyncMock()

    async def execute(self, stmt):  # noqa: ARG002
        return _Scalars(self._rows)


def _type_row(fields_json: str):
    return SimpleNamespace(id=1, fields=fields_json)


TEXT_ONLY = '[{"key": "title", "type": "text", "required": true}]'
TEXT_AND_NUMBER = '[{"key": "title", "type": "text", "required": true}, {"key": "price", "type": "number"}]'


@pytest.mark.asyncio
class TestSetValues:
    async def test_type_not_found(self):
        with patch(CRUD_GET, AsyncMock(return_value=None)):
            with pytest.raises(NotFoundError):
                await custom_post_type_service.set_values(FakeDB(), 1, 2, {"title": "x"})

    async def test_type_without_fields_is_rejected(self):
        with patch(CRUD_GET, AsyncMock(return_value=_type_row("[]"))):
            with pytest.raises(BadRequestError) as exc:
                await custom_post_type_service.set_values(FakeDB(), 1, 2, {"title": "x"})
        assert "尚未定义字段" in str(exc.value)

    async def test_undefined_key_is_rejected(self):
        with patch(CRUD_GET, AsyncMock(return_value=_type_row(TEXT_ONLY))):
            with pytest.raises(BadRequestError) as exc:
                await custom_post_type_service.set_values(FakeDB(), 1, 2, {"titel": "typo"})
        assert "titel" in str(exc.value), "拼错字段名必须报错，而不是静默丢数据"

    async def test_missing_required_is_rejected(self):
        with patch(CRUD_GET, AsyncMock(return_value=_type_row(TEXT_ONLY))):
            with pytest.raises(BadRequestError) as exc:
                await custom_post_type_service.set_values(FakeDB(), 1, 2, {"title": "  "})
        assert "title" in str(exc.value)

    async def test_type_mismatch_is_rejected(self):
        with patch(CRUD_GET, AsyncMock(return_value=_type_row(TEXT_AND_NUMBER))):
            with pytest.raises(BadRequestError):
                await custom_post_type_service.set_values(
                    FakeDB(), 1, 2, {"title": "t", "price": "很贵"}
                )

    async def test_inserts_new_rows_with_normalized_values(self):
        db = FakeDB()
        with patch(CRUD_GET, AsyncMock(return_value=_type_row(TEXT_AND_NUMBER))):
            result = await custom_post_type_service.set_values(
                db, 1, 2, {"title": "你好", "price": "12.50"}, user_id=9
            )

        assert result == {"type_id": 1, "content_id": 2, "updated": ["price", "title"]}
        assert len(db.added) == 2
        by_name = {row.field_name: row for row in db.added}
        assert by_name["price"].field_value == "12.5", "值应按定义规范化后入库"
        assert by_name["title"].user == 9
        assert db.commit.await_count == 1

    async def test_updates_existing_rows_instead_of_duplicating(self):
        existing = SimpleNamespace(field_name="title", field_value="旧标题")
        db = FakeDB([existing])
        with patch(CRUD_GET, AsyncMock(return_value=_type_row(TEXT_ONLY))):
            await custom_post_type_service.set_values(db, 1, 2, {"title": "新标题"})

        assert existing.field_value == "新标题"
        assert db.added == [], "已有值必须 upsert，不新增重复行"

    async def test_put_semantics_rejects_missing_required_fields(self):
        """PUT 是**全量**语义：必填字段缺失必须报错，而不是静默保留旧值。

        （若将来要支持局部更新，应另加 PATCH 端点并在合并后再校验。）
        """
        with patch(CRUD_GET, AsyncMock(return_value=_type_row(TEXT_AND_NUMBER))):
            with pytest.raises(BadRequestError) as exc:
                await custom_post_type_service.set_values(FakeDB(), 1, 2, {"price": 5})
        assert "title" in str(exc.value)

    async def test_optional_field_keeps_existing_value_when_absent(self):
        """可选字段未传时不清空（只有传了的字段才被更新）。"""
        existing = SimpleNamespace(field_name="title", field_value="保持")
        db = FakeDB([existing])
        with patch(CRUD_GET, AsyncMock(return_value=_type_row(TEXT_AND_NUMBER))):
            await custom_post_type_service.set_values(db, 1, 2, {"title": "新", "price": 5})

        assert existing.field_value == "新"
        added = {row.field_name for row in db.added}
        assert added == {"price"}, "只应写入本次传了的字段"


@pytest.mark.asyncio
class TestGetValues:
    async def test_type_not_found(self):
        with patch(CRUD_GET, AsyncMock(return_value=None)):
            with pytest.raises(NotFoundError):
                await custom_post_type_service.get_values(FakeDB(), 1, 2)

    async def test_missing_fields_are_filled_with_none(self):
        db = FakeDB([SimpleNamespace(field_name="title", field_value="你好")])
        with patch(CRUD_GET, AsyncMock(return_value=_type_row(TEXT_AND_NUMBER))):
            out = await custom_post_type_service.get_values(db, 1, 2)
        assert out["values"] == {"title": "你好", "price": None}

    async def test_values_not_in_definition_are_ignored(self):
        """库里存的历史字段若已从定义里删除，不再回传给前端。"""
        db = FakeDB([SimpleNamespace(field_name="legacy", field_value="旧字段")])
        with patch(CRUD_GET, AsyncMock(return_value=_type_row(TEXT_ONLY))):
            out = await custom_post_type_service.get_values(db, 1, 2)
        assert out["values"] == {"title": None}
