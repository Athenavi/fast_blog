"""CRUDBase 语句构造测试（Phase 1 验收）

只验证「查询构造」这一层的正确性与安全性（列名白名单、keyword、排序回退、软删除开关），
不连接数据库 —— 真正的读写由 Phase 2 起的模块级集成测试覆盖。
"""

from sqlalchemy import select

from shared.models.user import User
from src.api.v3.core.base_crud import CRUDBase


class UserCRUD(CRUDBase):
    model = User
    keyword_fields = ("username", "email")
    default_order_by = "id"


def _sql(stmt) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


def test_columns_reflect_model():
    crud = UserCRUD()
    assert "id" in crud.columns
    assert crud.primary_key == "id"


def test_filters_ignore_unknown_column_and_none_value():
    """非模型列名与 None 值都必须被忽略（防注入 + 避免误过滤）"""
    crud = UserCRUD()
    sql = _sql(crud._build_query({"id": 7, "definitely_not_a_column": 1, "username": None}))

    assert "definitely_not_a_column" not in sql
    where_clause = sql.split("WHERE", 1)[1]
    assert "username" not in where_clause
    assert "users.id = 7" in where_clause


def test_filters_support_in_clause():
    crud = UserCRUD()
    sql = _sql(crud._build_query({"id": [1, 2, 3]}))

    assert "id IN (1, 2, 3)" in sql


def test_keyword_search_uses_declared_fields():
    crud = UserCRUD()
    sql = _sql(crud._build_query(None, "alice"))
    where_clause = sql.split("WHERE", 1)[1]

    # 具体算子由方言决定（PostgreSQL 为 ILIKE，通用编译为 lower(...) LIKE），只断言语义
    assert "username" in where_clause
    assert "email" in where_clause
    assert "alice" in where_clause.lower()


def test_keyword_ignored_when_no_fields_declared():
    class NoKeywordCRUD(CRUDBase):
        model = User
        keyword_fields = ()

    sql = _sql(NoKeywordCRUD()._build_query(None, "alice"))
    assert "alice" not in sql


def test_order_falls_back_to_default_then_primary_key():
    crud = UserCRUD()
    assert "ORDER BY users.id DESC" in _sql(crud._apply_order(select(User), None, "desc"))
    assert "ORDER BY users.id ASC" in _sql(crud._apply_order(select(User), None, "asc"))
    # 非法列名 → 回退默认字段，而不是把用户输入拼进 SQL
    assert "ORDER BY users.id" in _sql(crud._apply_order(select(User), "1; DROP TABLE users", "asc"))

    class NoDefaultCRUD(CRUDBase):
        model = User
        default_order_by = "not_a_column"

    assert "ORDER BY users.id" in _sql(NoDefaultCRUD()._apply_order(select(User), None, "desc"))


def test_soft_delete_disabled_by_default():
    """默认不做软删除过滤：模型没有该字段时必须保持物理语义"""
    crud = UserCRUD()
    assert crud.soft_delete_enabled is False
    assert "IS NOT" not in _sql(crud._build_query({"id": 1})).upper()


def test_to_dict_accepts_pydantic_and_mapping():
    from pydantic import BaseModel

    class Payload(BaseModel):
        username: str
        email: str

    assert CRUDBase._to_dict(Payload(username="a", email="b")) == {"username": "a", "email": "b"}
    assert CRUDBase._to_dict({"username": "a"}) == {"username": "a"}
    assert CRUDBase._to_dict(None) == {}
