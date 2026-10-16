"""export 模块的纯函数 / 服务层测试

不连接数据库、不注册路由（模块登记由外部统一处理，避免与路由注册测试冲突）。
覆盖：

  - ``to_csv`` 的 BOM / 中文表头 / 字段顺序 / 特殊字符转义 / 特殊类型转换
  - ``templates()`` 结构
  - ``spec()`` 未知资源异常
  - ``EXPORT_RESOURCES`` 的字段 / 排序列 / 时间列 / 搜索列**是否都是真实模型列**
    （这正是 v2 踩过的坑：字段名与真表列不符）
"""

import csv
import io
from datetime import datetime

import pytest

from shared.models.analytics.page_view import PageView
from shared.models.article.article import Article
from shared.models.category.category import Category
from shared.models.comment.comment import Comment
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.permission import codes
from src.api.v3.modules.system.export.service import (
    EXPORT_RESOURCES,
    MAX_EXPORT_ROWS,
    ExportService,
    _resolve_limit,
    export_service,
    to_csv,
)

RESOURCES = ["users", "articles", "comments", "categories", "page_views"]

EXPECTED_MODELS = {
    "users": User,
    "articles": Article,
    "comments": Comment,
    "categories": Category,
    "page_views": PageView,
}


def _decode(payload: bytes) -> str:
    return payload.decode("utf-8-sig")


def _parse(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def _fields(resource: str) -> list[dict]:
    return list(EXPORT_RESOURCES[resource]["fields"])


# ---------------------------------------------------------------- 登记表完整性
def test_required_resources_registered():
    assert set(EXPORT_RESOURCES) >= set(RESOURCES)
    for resource, model in EXPECTED_MODELS.items():
        assert EXPORT_RESOURCES[resource]["model"] is model


@pytest.mark.parametrize("resource", RESOURCES)
def test_every_field_is_a_real_model_column(resource):
    """字段必须是真实列名（否则真表查询会 KeyError）且中文表头非空、无重复"""
    real_columns = set(EXPORT_RESOURCES[resource]["model"].__table__.columns.keys())
    keys = []
    for field in _fields(resource):
        assert field["key"] in real_columns, f"{resource}.{field['key']} 不是真实列"
        assert field["label"], f"{resource}.{field['key']} 缺少中文表头"
        keys.append(field["key"])
    assert len(keys) == len(set(keys)), f"{resource} 存在重复字段"


@pytest.mark.parametrize("resource", RESOURCES)
def test_sort_and_filter_columns_are_real(resource):
    spec = EXPORT_RESOURCES[resource]
    real_columns = set(spec["model"].__table__.columns.keys())
    assert spec["order_by"] in real_columns
    assert spec["time_field"] in real_columns
    for column in spec["search_fields"]:
        assert column in real_columns


def test_registered_permissions_are_known_codes():
    known = set(codes.all_codes())
    for resource, spec in EXPORT_RESOURCES.items():
        assert spec["permission"] in known, resource


def test_users_export_excludes_sensitive_columns():
    keys = {field["key"] for field in _fields("users")}
    assert {"username", "last_login_at", "date_joined"} <= keys
    assert keys.isdisjoint({"password", "totp_secret", "backup_codes"})


# ---------------------------------------------------------------- templates()
def test_templates_structure():
    data = export_service.templates()
    assert data["count"] == len(EXPORT_RESOURCES)
    assert len(data["resources"]) == data["count"]

    by_name = {item["resource"]: item for item in data["resources"]}
    assert set(by_name) == set(EXPORT_RESOURCES)

    users = by_name["users"]
    assert users["label"] == "用户"
    assert users["permission"].startswith("module_")
    keys = [field["key"] for field in users["fields"]]
    assert "username" in keys and "last_login_at" in keys


# ---------------------------------------------------------------- spec()
def test_spec_unknown_resource_raises_not_found():
    with pytest.raises(NotFoundError):
        export_service.spec("does-not-exist")


def test_spec_returns_registration():
    spec = export_service.spec("articles")
    assert spec["model"] is Article
    assert spec["order_by"] == "id"
    assert ExportService().spec("comments")["label"] == "评论"


# ---------------------------------------------------------------- _resolve_limit
def test_resolve_limit_bounds():
    assert _resolve_limit(None) == MAX_EXPORT_ROWS
    assert _resolve_limit(100) == 100
    with pytest.raises(BadRequestError):
        _resolve_limit(0)
    with pytest.raises(BadRequestError):
        _resolve_limit(MAX_EXPORT_ROWS + 1)


# ---------------------------------------------------------------- to_csv
def test_to_csv_has_bom_and_chinese_header():
    fields = [{"key": "id", "label": "ID"}, {"key": "username", "label": "用户名"}]
    payload = to_csv([{"id": 1, "username": "alice"}], fields)

    assert payload.startswith(b"\xef\xbb\xbf")
    assert payload.decode("utf-8").startswith("\ufeff")
    parsed = _parse(_decode(payload))
    assert parsed[0] == ["ID", "用户名"]
    assert parsed[1] == ["1", "alice"]


def test_to_csv_respects_field_order_not_row_key_order():
    fields = [{"key": "b", "label": "乙"}, {"key": "a", "label": "甲"}]
    parsed = _parse(_decode(to_csv([{"a": 1, "b": 2}], fields)))
    assert parsed[0] == ["乙", "甲"]
    assert parsed[1] == ["2", "1"]


def test_to_csv_without_bom():
    payload = to_csv([{"a": "x"}], [{"key": "a", "label": "A"}], with_bom=False)
    assert not payload.startswith(b"\xef\xbb\xbf")
    # CSV 有表头行，且标准行尾是 CRLF（csv 模块默认）
    assert payload.decode("utf-8").startswith("A\r\nx")


def test_to_csv_escapes_special_characters():
    fields = [{"key": "content", "label": "内容"}]
    rows = [{"content": 'a,b "c"\nd'}]
    parsed = _parse(_decode(to_csv(rows, fields)))
    assert parsed[0] == ["内容"]
    assert parsed[1] == ['a,b "c"\nd']


def test_to_csv_special_types():
    fields = [
        {"key": "flag", "label": "标志"},
        {"key": "off", "label": "关闭"},
        {"key": "empty", "label": "空"},
        {"key": "when", "label": "时间"},
        {"key": "tags", "label": "标签"},
    ]
    rows = [
        {
            "flag": True,
            "off": False,
            "empty": None,
            "when": datetime(2026, 1, 2, 3, 4, 5),
            "tags": ["x", "y"],
        }
    ]
    parsed = _parse(_decode(to_csv(rows, fields)))
    assert parsed[1] == ["是", "否", "", "2026-01-02 03:04:05", '["x", "y"]']


def test_to_csv_empty_rows_still_writes_header():
    fields = [{"key": "id", "label": "ID"}]
    parsed = _parse(_decode(to_csv([], fields)))
    assert parsed == [["ID"]]


def test_to_csv_missing_key_becomes_empty_cell():
    fields = [{"key": "id", "label": "ID"}, {"key": "name", "label": "名称"}]
    parsed = _parse(_decode(to_csv([{"id": 7}], fields)))
    assert parsed[1] == ["7", ""]
