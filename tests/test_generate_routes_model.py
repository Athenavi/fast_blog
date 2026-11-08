"""批次 21：模型生成器两个缺陷的回归测试（`scripts/generate_routes.py` + 模板）

修的两个缺陷（memory 记的 P6 ③④）：

  ③ **`nullable: false` 没有被生成**：模板只有 `nullable=True` 分支，于是 yaml 里写
     `nullable: false` 的整数/布尔/外键列生成出来仍是可空的；
  ④ **`indexes` 里 `unique: true` 的项被渲染两遍**：既生成同名 `UniqueConstraint` 又生成
     `Index(name, unique=True)`，PostgreSQL 建表直接报 `DuplicateTableError`
     （批次 20 用 `create_all` 实测到）。

这里直接渲染模板（不落盘、不碰 `shared/models/`），断言生成的列定义与表级参数。
"""

import yaml

from scripts.generate_routes import RouteGenerator

MODEL_NAME = "UnitTestModel"

MINIMAL_CONFIG = {
    "models": {
        MODEL_NAME: {
            "description": "生成器测试模型",
            "orm": True,
            "table": "unit_test_models",
            "module": "unittest",
            "properties": {
                "id": {"type": "bigint", "description": "ID"},
                "user_id": {
                    "type": "bigint",
                    "foreignKey": "User",
                    "nullable": False,
                    "description": "归属用户",
                },
                "count": {"type": "integer", "nullable": False, "default": 0, "description": "计数"},
                "note": {"type": "string", "nullable": True, "description": "备注"},
                "extra": {"type": "integer", "description": "未声明 nullable（应保持 SQLAlchemy 默认）"},
                "secret_value": {
                    "type": "string",
                    "maxLength": 64,
                    "nullable": True,
                    "encrypted": True,
                    "description": "加密字符串",
                },
                "secret_blob": {
                    "type": "text",
                    "nullable": True,
                    "encrypted": True,
                    "description": "加密文本",
                },
            },
            "indexes": [
                {"name": "idx_unit_test_models_code", "columns": ["note"], "unique": True},
                {"name": "idx_unit_test_models_user", "columns": ["user_id"]},
            ],
        }
    }
}


def _render(tmp_path) -> str:  # noqa: ANN001 - pytest tmp_path
    config_path = tmp_path / "models.yaml"
    config_path.write_text(yaml.safe_dump(MINIMAL_CONFIG, allow_unicode=True), encoding="utf-8")
    generator = RouteGenerator(str(config_path))

    model_def = generator.models[MODEL_NAME]
    fields = generator._convert_properties_to_fields(
        model_def["properties"],
        model_name=MODEL_NAME,
        all_models=generator.models,
        table_prefix="",
    )
    indexes, unique_constraints = generator._split_indexes(model_def)
    template = generator.jinja_env.get_template("sqlalchemy_model.py.jinja2")
    return template.render(
        model_name=MODEL_NAME,
        generation_time="2026-01-01 00:00:00",
        classes={
            MODEL_NAME: {
                "table_name": model_def["table"],
                "description": model_def["description"],
                "fields": fields,
                "relationships": {},
                "indexes": indexes,
                "unique_constraints": unique_constraints,
            }
        },
        module_path="unittest",
        table_prefix="",
        table_has_indexes=bool(indexes),
        table_has_unique_constraints=bool(unique_constraints),
        has_foreign_keys=any(field.get("foreign_key") for field in fields.values()),
        has_unique_constraints=bool(unique_constraints),
        has_datetime_default=False,
        has_numeric=False,
        has_relationships=False,
        has_encrypted=any(field.get("encrypted") for field in fields.values()),
        relationship_imports=generator._relationship_imports(
            MODEL_NAME, model_def, generator.models
        ),
        is_unlogged=False,
        custom_methods={},
        ns=type("NS", (), {"has_uuid_pk": False, "has_datetime_default": False})(),
        all_models=generator.models,
    )


def _column_line(rendered: str, column: str) -> str:
    return next(line for line in rendered.splitlines() if line.strip().startswith(f"{column} = Column"))


# ================================================================ ③ nullable 三态
def test_nullable_false_is_emitted_for_integer(tmp_path) -> None:  # noqa: ANN001
    """yaml 写 nullable: false 的整数列必须生成 nullable=False（缺陷③）"""
    line = _column_line(_render(tmp_path), "count")
    assert "nullable=False" in line


def test_nullable_false_is_emitted_for_foreign_key(tmp_path) -> None:  # noqa: ANN001
    """外键分支曾有局部变量覆盖了三态处理，同样要支持 nullable: false"""
    line = _column_line(_render(tmp_path), "user_id")
    assert "ForeignKey('users.id')" in line
    assert "nullable=False" in line


def test_nullable_true_is_emitted_for_string(tmp_path) -> None:  # noqa: ANN001
    line = _column_line(_render(tmp_path), "note")
    assert "nullable=True" in line


def test_undeclared_nullable_keeps_default(tmp_path) -> None:  # noqa: ANN001
    """未声明 nullable 的列**不能**凭空生成 nullable=False（否则会改既有模型语义）"""
    line = _column_line(_render(tmp_path), "extra")
    column_part = line.split(", doc=")[0]  # doc 文案里也可能出现 "nullable" 字样
    assert "nullable" not in column_part


# ================================================================ ④ unique 索引只生成一种
def test_unique_index_becomes_unique_constraint_only(tmp_path) -> None:  # noqa: ANN001
    """unique:true 的项只出现 UniqueConstraint，且不再重复渲染同名 Index（缺陷④）"""
    rendered = _render(tmp_path)
    assert "UniqueConstraint('note', name='idx_unit_test_models_code')" in rendered
    assert "Index('idx_unit_test_models_code'" not in rendered
    # 普通索引照旧生成
    assert "Index('idx_unit_test_models_user', 'user_id')" in rendered


def test_unique_only_table_does_not_import_index(tmp_path) -> None:  # noqa: ANN001
    """表里只有 unique 索引时，不应该 import 用不到的 Index（否则 ruff F401）"""
    config_path = tmp_path / "models.yaml"
    config = {
        "models": {
            MODEL_NAME: {
                **MINIMAL_CONFIG["models"][MODEL_NAME],
                "indexes": [{"name": "idx_only_unique", "columns": ["note"], "unique": True}],
            }
        }
    }
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    generator = RouteGenerator(str(config_path))
    model_def = generator.models[MODEL_NAME]
    fields = generator._convert_properties_to_fields(
        model_def["properties"], model_name=MODEL_NAME, all_models=generator.models, table_prefix=""
    )
    indexes, unique_constraints = generator._split_indexes(model_def)
    rendered = generator.jinja_env.get_template("sqlalchemy_model.py.jinja2").render(
        model_name=MODEL_NAME,
        generation_time="2026-01-01 00:00:00",
        classes={
            MODEL_NAME: {
                "table_name": model_def["table"],
                "description": model_def["description"],
                "fields": fields,
                "relationships": {},
                "indexes": indexes,
                "unique_constraints": unique_constraints,
            }
        },
        module_path="unittest",
        table_prefix="",
        table_has_indexes=bool(indexes),
        table_has_unique_constraints=bool(unique_constraints),
        has_foreign_keys=any(field.get("foreign_key") for field in fields.values()),
        has_unique_constraints=bool(unique_constraints),
        has_datetime_default=False,
        has_numeric=False,
        has_relationships=False,
        is_unlogged=False,
        custom_methods={},
        ns=type("NS", (), {"has_uuid_pk": False, "has_datetime_default": False})(),
        all_models=generator.models,
    )
    assert "UniqueConstraint('note', name='idx_only_unique')" in rendered
    assert "Index(" not in rendered
    assert "from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime" in rendered


def test_split_indexes_keeps_order_and_partitions() -> None:
    split = RouteGenerator._split_indexes(
        {
            "indexes": [
                {"name": "a", "columns": ["x"], "unique": True},
                {"name": "b", "columns": ["y"]},
                {"name": "c", "columns": ["z"]},
            ]
        }
    )
    assert [item["name"] for item in split[0]] == ["b", "c"]
    assert [item["name"] for item in split[1]] == ["a"]

# ================================================================ ⑤ 加密字段 / 关联导入
def test_encrypted_fields_render_encrypted_field(tmp_path) -> None:  # noqa: ANN001
    """yaml 标 `encrypted: true` 的列必须生成 EncryptedField，且导入对应类型"""
    rendered = _render(tmp_path)
    assert "from shared.utils.crypto import EncryptedField" in rendered
    assert "EncryptedField(String(64))" in _column_line(rendered, "secret_value")
    assert "EncryptedField(Text)" in _column_line(rendered, "secret_blob")


def test_relationship_imports_cover_target_and_secondary() -> None:
    """relationship() 用到的目标模型与中间表必须被提前导入（否则 mapper 配置失败）"""
    generator = RouteGenerator.__new__(RouteGenerator)
    all_models = {
        "User": {"module": "user", "table": "users"},
        "Role": {"module": "rbac", "table": "roles"},
        "UserRole": {"module": "rbac", "table": "user_role_assignments"},
    }
    model_def = {
        "relationships": {
            "roles": {
                "target": "Role",
                "secondary": "user_role_assignments",
                "back_populates": "users",
            }
        }
    }
    imports = generator._relationship_imports("User", model_def, all_models)
    assert imports == ["shared.models.rbac.role", "shared.models.rbac.user_role"]

def test_model_file_name_can_be_overridden() -> None:
    """文件名不总是能由模型名派生（CollaborationInvite → invitation.py），yaml 可覆盖"""
    generator = RouteGenerator.__new__(RouteGenerator)
    assert generator._model_file_stem("CollaborationInvite", {"file": "invitation"}) == "invitation"
    assert generator._model_file_stem("User", {}) == "user"

