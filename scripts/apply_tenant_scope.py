"""把租户级表批量纳入站点隔离（改 models.yaml + 模型文件 + 生成 Alembic 迁移）

为什么用脚本而不是手工：站点级表有上百张，逐张改 yaml 与模型文件既慢又容易漏，
而且"改了 yaml 忘了改模型"或反之都会造成运行期不一致。脚本把「纳入哪些表」
收敛到 ``config/tenancy.yaml`` 一个清单，可重复执行、可审计。

用法::

    python -m scripts.apply_tenant_scope --check    # 只报告将会改动什么（不写文件）
    python -m scripts.apply_tenant_scope --apply    # 落地（幂等，已加的会跳过）

落地的三件事：

1. ``config/models.yaml``：给清单中的模型补 ``site_id`` 属性；
2. ``shared/models/**/*.py``：给对应模型补 ``site_id = Column(BigInteger, …)``；
3. 生成一条 Alembic 迁移，对尚未加列的表 ``add_column``（``--skip-migration`` 可关）。

**刻意不加数据库外键**：``site_id`` 用普通 BigInteger + 索引。加外键会让"删除站点"
级联删掉其全部内容，而多租户场景需要的是"先迁移内容、再删站点"的显式流程。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_YAML = PROJECT_ROOT / "config" / "models.yaml"
TENANCY_YAML = PROJECT_ROOT / "config" / "tenancy.yaml"
MODELS_DIR = PROJECT_ROOT / "shared" / "models"
VERSIONS_DIR = PROJECT_ROOT / "alembic_migrations" / "versions"

COLUMN_DOC = "所属站点 ID（多租户隔离键）"


def load_scope() -> Tuple[List[str], List[str]]:
    data = yaml.safe_load(TENANCY_YAML.read_text(encoding="utf-8")) or {}
    tenant = list(data.get("tenant_tables") or [])
    excluded = list(data.get("excluded_tables") or [])
    duplicates = set(tenant) & set(excluded)
    if duplicates:
        raise SystemExit(f"tenancy.yaml 中同时出现在两边的表：{sorted(duplicates)}")
    return tenant, excluded


def all_tables() -> Dict[str, str]:
    """扫描模型文件，返回 ``{表名: 文件路径}``"""
    found: Dict[str, str] = {}
    pattern = re.compile(r"__tablename__\s*=\s*['\"]([\w]+)['\"]")
    for path in MODELS_DIR.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        for table in pattern.findall(text):
            found[table] = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    return found


def report_unclassified(tables: Dict[str, str], tenant: List[str], excluded: List[str]) -> List[str]:
    known = set(tenant) | set(excluded)
    return sorted(set(tables) - known)


# ---------------------------------------------------------------- models.yaml
def _model_names_in_yaml(text: str) -> List[str]:
    """提取 ``models:`` 下二级键（模型名）"""
    names: List[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("models:"):
            inside = True
            continue
        if not inside:
            continue
        if line and not line.startswith(" "):
            break  # 顶层键，说明 models 段结束
        match = re.match(r"^  (\w+):\s*$", line)
        if match:
            names.append(match.group(1))
    return names


def _table_to_model(text: str) -> Dict[str, str]:
    """``{表名: 模型名}``（同一个模型块内的 table: 字段）"""
    mapping: Dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        model = re.match(r"^  (\w+):\s*$", line)
        if model:
            current = model.group(1)
            continue
        table = re.match(r"^    table:\s*(\w+)\s*$", line)
        if table and current:
            mapping[table.group(1)] = current
    return mapping


def _models_with_site_id(text: str) -> set:
    """已经声明了 site_id 的模型名

    脚本必须可重复执行（``--apply`` 会跑多次），否则会把 site_id 插入第二遍。
    """
    found: set = set()
    current = None
    for line in text.splitlines():
        model = re.match(r"^  (\w+):\s*$", line)
        if model:
            current = model.group(1)
            continue
        if current and re.match(r"^      site_id:\s*$", line):
            found.add(current)
    return found


def patch_models_yaml(text: str, tenant_tables: List[str]) -> Tuple[str, List[str]]:
    """在每个待纳入模型的 ``properties:`` 之后插入 site_id；返回 (新文本, 已改动的模型名)"""
    table_to_model = _table_to_model(text)
    targets = {
        table_to_model[table]
        for table in tenant_tables
        if table in table_to_model
    }
    # 幂等：已经有 site_id 的模型不再处理
    targets -= _models_with_site_id(text)
    lines = text.splitlines(keepends=True)
    out: List[str] = []
    current: str | None = None
    changed: List[str] = []
    pending_insert = False

    for line in lines:
        model = re.match(r"^  (\w+):\s*$", line)
        if model:
            current = model.group(1)
        if pending_insert and re.match(r"^      \w+:", line):
            out.append(
                "      site_id:\n"
                "        type: bigint\n"
                "        nullable: true\n"
                f"        description: {COLUMN_DOC}\n"
            )
            changed.append(current or "")
            pending_insert = False
        if current in targets and re.match(r"^    properties:\s*$", line):
            pending_insert = True
        out.append(line)

    return "".join(out), changed


# --------------------------------------------------------------- 模型文件
def patch_model_file(text: str, table: str) -> Tuple[str, bool]:
    """给 ``__tablename__ = '<table>'`` 所在的类补 site_id 列"""
    lines = text.splitlines(keepends=True)
    out: List[str] = []
    inserted = False
    marker = re.compile(rf"__tablename__\s*=\s*['\"]{re.escape(table)}['\"]")
    for index, line in enumerate(lines):
        out.append(line)
        if inserted or not marker.search(line):
            continue
        if "site_id" in text:
            return text, False  # 已经有（可能别的类），不重复插
        # 往后找类体内第一个 "    <name> = Column(" 作为插入点
        for offset in range(index + 1, len(lines)):
            if re.match(r"^    \w+ = Column\(", lines[offset]):
                out.extend(lines[index + 1: offset])
                out.append(f"    site_id = Column(BigInteger, nullable=True, index=True, doc='{COLUMN_DOC}')\n")
                inserted = True
                for rest in lines[offset:]:
                    out.append(rest)
                return "".join(out), True
    return text, False


def ensure_biginteger_import(text: str) -> Tuple[str, bool]:
    """确保 ``from sqlalchemy import …`` 里有 BigInteger

    必须兼容**两种写法** —— 仓库里两者都有：

    - 单行：``from sqlalchemy import BigInteger, Boolean, Column``
    - 多行：``from sqlalchemy import (\\n    BigInteger,\\n    …\\n)``

    早期实现只处理单行，遇到多行形式会把 ``(`` 当成一个条目，产出
    ``from sqlalchemy import BigInteger, (`` 这种非法语法（已实际发生过，
    且因为 ``alembic heads`` 不执行 env.py 而没有被发现）。
    """
    paren = re.search(r"^from sqlalchemy import \(\n", text, flags=re.MULTILINE)
    if paren:
        block_end = text.find("\n)", paren.end())
        body = text[paren.end(): block_end] if block_end != -1 else ""
        if re.search(r"^\s*BigInteger\b", body, flags=re.MULTILINE):
            return text, False
        return text[: paren.end()] + "    BigInteger,\n" + text[paren.end():], True

    match = re.search(r"^from sqlalchemy import ([^\n]+)$", text, flags=re.MULTILINE)
    if not match:
        return text, False
    imported = [item.strip() for item in match.group(1).split(",") if item.strip()]
    if "BigInteger" in imported:
        return text, False
    imported.insert(0, "BigInteger")
    replacement = "from sqlalchemy import " + ", ".join(imported)
    return text[: match.start()] + replacement + text[match.end():], True


# ------------------------------------------------------------------ 迁移
def build_migration(tables: List[str], down_revision: str) -> Tuple[str, str]:
    revision = "e5f1b8c93a07"
    filename = f"{revision}_add_site_id_tenant_scope.py"
    upgrades = "\n".join(
        f"    op.add_column(\n"
        f"        '{table}',\n"
        f"        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='{COLUMN_DOC}'),\n"
        f"    )\n"
        f"    op.create_index('ix_{table}_site_id', '{table}', ['site_id'])\n"
        for table in tables
    )
    downgrades = "\n".join(
        f"    op.drop_index('ix_{table}_site_id', table_name='{table}')\n"
        f"    op.drop_column('{table}', 'site_id')\n"
        for table in reversed(tables)
    )
    #: 存量数据归属默认站点。不回填的话，隔离上线后 site_id IS NULL 的行
    #: 对所有站点都不可见 —— 表现为"升级后内容全没了"。
    #: sites 表为空时 COALESCE 为 NULL，UPDATE 退化成空操作（安全）。
    default_site_sql = (
        "COALESCE("
        "(SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),"
        "(SELECT id FROM sites ORDER BY id LIMIT 1))"
    )
    backfill = "\n".join(
        f"    op.execute(\n"
        f"        \"UPDATE {table} SET site_id = {default_site_sql} WHERE site_id IS NULL\"\n"
        f"    )\n"
        for table in tables
    )
    content = f'''"""add site_id tenant scope

Revision ID: {revision}
Revises: {down_revision}
Create Date: 2026-10-14 00:00:00.000000

给**站点级**表补 ``site_id``：多租户隔离的落点。清单与判定原则见 ``config/tenancy.yaml``，
由 ``python -m scripts.apply_tenant_scope`` 生成。

隔离行为由 ``src/api/v3/core/tenancy.py`` + ``base_crud._apply_site_scope`` 实现：
有 ``site_id`` 列 + 上下文有站点 + 未显式跨站点，三者同时成立才收窄查询。

``nullable=True`` 且**不回填**：存量数据归属由部署者决定（通常是默认站点），
回填脚本用 ``UPDATE <table> SET site_id = <默认站点ID> WHERE site_id IS NULL``。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '{revision}'
down_revision: Union[str, Sequence[str], None] = '{down_revision}'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
{upgrades}
    # ---- 存量数据回填 ----
    # 不回填的话，隔离上线后这些行（site_id IS NULL）对**所有**站点都不可见，
    # 表现为"升级后内容全没了"。这里统一归属默认站点（未标默认则取最早的一个）；
    # sites 表为空时 COALESCE 得到 NULL，UPDATE 成为空操作。
{backfill}

def downgrade() -> None:
    """Downgrade schema."""
{downgrades}
'''
    return filename, content


def current_head() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic_migrations"))
    return ScriptDirectory.from_config(config).get_current_head()


def main() -> int:
    parser = argparse.ArgumentParser(description="把租户级表纳入站点隔离")
    parser.add_argument("--apply", action="store_true", help="真正写文件（默认只检查）")
    parser.add_argument("--check", action="store_true", help="只报告差异（默认行为）")
    parser.add_argument("--skip-migration", action="store_true", help="不改 alembic 迁移")
    args = parser.parse_args()
    apply = args.apply

    tenant, excluded = load_scope()
    tables = all_tables()
    unclassified = report_unclassified(tables, tenant, excluded)

    missing = sorted(set(tenant) - set(tables))
    if missing:
        print(f"[warn] tenancy.yaml 里这些表在模型文件中找不到：{missing}")
    if unclassified:
        print(f"[warn] 未分类的表（请显式归入 tenant_tables 或 excluded_tables）：{unclassified}")

    yaml_text = MODELS_YAML.read_text(encoding="utf-8")
    new_yaml, yaml_models = patch_models_yaml(yaml_text, tenant)

    table_to_file = {table: tables[table] for table in tenant if table in tables}
    file_changes: Dict[str, List[str]] = {}
    for table, rel in table_to_file.items():
        path = PROJECT_ROOT / rel
        text = path.read_text(encoding="utf-8")
        if re.search(rf"^\s+site_id = Column", text, flags=re.MULTILINE):
            continue
        updated, changed = patch_model_file(text, table)
        if changed:
            updated, _ = ensure_biginteger_import(updated)
            file_changes.setdefault(rel, []).append(table)
            if apply:
                path.write_text(updated, encoding="utf-8")

    if apply and yaml_models:
        MODELS_YAML.write_text(new_yaml, encoding="utf-8")

    print(f"models.yaml: {'已更新' if apply else '将更新'} {len(yaml_models)} 个模型")
    print(f"模型文件: {'已更新' if apply else '将更新'} {len(file_changes)} 个文件")
    for rel, items in sorted(file_changes.items()):
        print(f"  - {rel}: {', '.join(items)}")

    if not args.skip_migration:
        pending = sorted(set(table_to_file))
        filename, content = build_migration(pending, current_head())
        target = VERSIONS_DIR / filename
        if target.exists():
            print(f"迁移已存在，跳过：{filename}")
        elif apply:
            target.write_text(content, encoding="utf-8")
            print(f"迁移已生成：{filename}（{len(pending)} 张表）")
        else:
            print(f"将生成迁移：{filename}（{len(pending)} 张表）")

    if not apply:
        print("\n提示：加 --apply 才会真正写文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
