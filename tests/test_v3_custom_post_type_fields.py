# -*- coding: utf-8 -*-
"""P1-3 内容建模器：字段定义与取值校验（纯函数，不依赖数据库）。

关注两类"必须显式失败"的行为：

  1. **非法字段定义**不得落库（key 规范/类型白名单/select 必带 options/relation 必带 target/重复 key/超上限）；
  2. **取值**按定义校验并规范化：必填缺失、超范围、选项外取值、拼错字段名（未定义 key）都要报错，
     而不是静默截断或丢弃；正常值要按类型规范化成可入库字符串。
"""

import json

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.content.custom_post_type.field_spec import (
    MAX_FIELDS,
    dump_fields,
    parse_fields,
    validate_field_definitions,
    validate_values,
)
from src.api.v3.modules.content.custom_post_type.schema import CustomPostTypeCreate


# ---------------------------------------------------------------- 定义校验

class TestFieldDefinitions:
    def test_accepts_minimal_and_normalizes(self):
        defs = validate_field_definitions('[{"key":"price","type":"number","label":"价格"}]')
        assert defs == [{"key": "price", "type": "number", "label": "价格"}]

    def test_empty_inputs_yield_empty_list(self):
        for raw in (None, "", []):
            assert validate_field_definitions(raw) == []

    def test_rejects_bad_json(self):
        with pytest.raises(BadRequestError) as exc:
            validate_field_definitions("{not json}")
        assert "JSON" in str(exc.value)

    def test_rejects_non_array(self):
        with pytest.raises(BadRequestError):
            validate_field_definitions('{"key":"a"}')

    @pytest.mark.parametrize("key", ["Price", "1price", "has space", "价格", "", "a" * 60])
    def test_rejects_invalid_keys(self, key):
        with pytest.raises(BadRequestError):
            validate_field_definitions(json.dumps([{"key": key, "type": "text"}]))

    def test_rejects_unknown_type(self):
        with pytest.raises(BadRequestError) as exc:
            validate_field_definitions(json.dumps([{"key": "x", "type": "wysiwyg"}]))
        assert "不支持" in str(exc.value)

    def test_rejects_duplicate_keys(self):
        with pytest.raises(BadRequestError) as exc:
            validate_field_definitions(
                json.dumps([{"key": "a", "type": "text"}, {"key": "a", "type": "text"}])
            )
        assert "重复" in str(exc.value)

    def test_select_requires_options(self):
        with pytest.raises(BadRequestError):
            validate_field_definitions(json.dumps([{"key": "lvl", "type": "select"}]))
        ok = validate_field_definitions(
            json.dumps([{"key": "lvl", "type": "select", "options": ["a", "b"]}])
        )
        assert ok[0]["options"] == ["a", "b"]

    def test_relation_requires_target(self):
        with pytest.raises(BadRequestError):
            validate_field_definitions(json.dumps([{"key": "rel", "type": "relation"}]))
        ok = validate_field_definitions(
            json.dumps([{"key": "rel", "type": "relation", "target": "tag", "multiple": True}])
        )
        assert ok[0]["target"] == "tag" and ok[0]["multiple"] is True

    def test_number_bounds_must_be_numeric(self):
        with pytest.raises(BadRequestError):
            validate_field_definitions(
                json.dumps([{"key": "n", "type": "number", "min": "低"}])
            )

    def test_too_many_fields_rejected(self):
        payload = [{"key": f"f{i}", "type": "text"} for i in range(MAX_FIELDS + 1)]
        with pytest.raises(BadRequestError) as exc:
            validate_field_definitions(json.dumps(payload))
        assert "上限" in str(exc.value)

    def test_parse_and_dump_roundtrip(self):
        raw = dump_fields([{"type": "text", "key": "a"}])
        assert parse_fields(raw) == [{"type": "text", "key": "a"}]
        assert parse_fields("not-json") == []


# ---------------------------------------------------------------- 取值校验

class TestValueValidation:
    SPECS = [
        {"key": "title", "type": "text", "required": True},
        {"key": "price", "type": "number", "min": 0, "max": 100},
        {"key": "visible", "type": "boolean"},
        {"key": "level", "type": "select", "options": ["a", "b"]},
        {"key": "tags", "type": "relation", "target": "tag", "multiple": True},
        {"key": "published_on", "type": "date"},
        {"key": "meta", "type": "json"},
    ]

    def test_missing_required_rejected(self):
        with pytest.raises(BadRequestError) as exc:
            validate_values(self.SPECS, {"price": 1})
        assert "title" in str(exc.value)

    def test_unknown_key_rejected(self):
        with pytest.raises(BadRequestError) as exc:
            validate_values(self.SPECS, {"title": "t", "titel": "typo"})
        assert "titel" in str(exc.value)

    def test_number_range_and_normalization(self):
        assert validate_values(self.SPECS, {"title": "t", "price": "12.50"})["price"] == "12.5"
        assert validate_values(self.SPECS, {"title": "t", "price": 3.0})["price"] == "3"
        with pytest.raises(BadRequestError):
            validate_values(self.SPECS, {"title": "t", "price": 101})
        with pytest.raises(BadRequestError):
            validate_values(self.SPECS, {"title": "t", "price": "贵"})

    def test_boolean_normalization(self):
        assert validate_values(self.SPECS, {"title": "t", "visible": True})["visible"] == "true"
        assert validate_values(self.SPECS, {"title": "t", "visible": "off"})["visible"] == "false"
        with pytest.raises(BadRequestError):
            validate_values(self.SPECS, {"title": "t", "visible": "maybe"})

    def test_select_must_be_allowed(self):
        assert validate_values(self.SPECS, {"title": "t", "level": "a"})["level"] == "a"
        with pytest.raises(BadRequestError):
            validate_values(self.SPECS, {"title": "t", "level": "z"})

    def test_relation_multiple_and_single(self):
        out = validate_values(self.SPECS, {"title": "t", "tags": ["tag-1", 2]})
        assert out["tags"] == "tag-1,2"
        with pytest.raises(BadRequestError):
            validate_values(self.SPECS, {"title": "t", "tags": ["bad value!"]})
        with pytest.raises(BadRequestError):
            validate_values(self.SPECS, {"title": "t", "tags": []})

    def test_date_must_be_iso(self):
        assert validate_values(self.SPECS, {"title": "t", "published_on": "2026-10-12"})[
                   "published_on"
               ] == "2026-10-12"
        with pytest.raises(BadRequestError):
            validate_values(self.SPECS, {"title": "t", "published_on": "12/10/2026"})

    def test_json_must_parse(self):
        assert validate_values(self.SPECS, {"title": "t", "meta": {"a": 1}})["meta"] == '{"a": 1}'
        with pytest.raises(BadRequestError):
            validate_values(self.SPECS, {"title": "t", "meta": "{broken"})

    def test_blank_optional_is_skipped(self):
        out = validate_values(self.SPECS, {"title": "t", "price": None, "level": "  "})
        assert "price" not in out and "level" not in out

    def test_too_long_text_rejected(self):
        with pytest.raises(BadRequestError) as exc:
            validate_values(self.SPECS, {"title": "x" * 300})
        assert "255" in str(exc.value)


# ---------------------------------------------------------------- schema 接入

class TestSchemaIntegration:
    def test_create_normalizes_field_definitions(self):
        payload = CustomPostTypeCreate(
            name="商品",
            slug="product",
            fields=json.dumps([{"type": "text", "key": "sku", "label": "货号"}]),
        )
        assert json.loads(payload.fields) == [{"key": "sku", "type": "text", "label": "货号"}]

    def test_create_rejects_invalid_definitions_at_input(self):
        # 定义非法时**直接抛 BadRequestError（400）**而不是被 pydantic 包装成 422 ——
        # "字段定义写错了"属于请求内容语义问题，400 比 422 更准确。
        with pytest.raises(BadRequestError) as exc:
            CustomPostTypeCreate(name="X", slug="x", fields=json.dumps([{"key": "A", "type": "text"}]))
        assert "key" in str(exc.value)

    def test_create_without_fields_stays_null(self):
        # 未传 fields → NULL（"未定义自定义字段"），与显式传 ``[]``（清空）区分开；
        # pydantic 对使用默认值的字段不做校验，因此这里不会被规范化成 "[]"。
        payload = CustomPostTypeCreate(name="X", slug="x")
        assert payload.fields is None

    def test_create_with_explicit_empty_array_becomes_empty_json(self):
        payload = CustomPostTypeCreate(name="X", slug="x", fields="[]")
        assert payload.fields == "[]"
