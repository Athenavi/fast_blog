#!/usr/bin/env python3
"""后台菜单种子（源：``frontend/web/src/utils/menus.ts``）

在"混合"决策下，**前端菜单表是菜单结构的唯一真相**（后端只管"哪些菜单被授权"），
因此本脚本把 ``ADMIN_MENUS`` 同步进后端 ``admin_menus``：

  - ``code`` = 条目的 ``name``（如 ``UserList``，与后端 ``admin_menus.code`` 一一对应）
  - ``title`` = ``title``
  - ``permission_code`` = ``permission``（缺省表示仅需登录）
  - ``menu_type``：带 ``children`` → 1（目录），否则 2（菜单）
  - ``parent_id`` 由层级推导；``hidden: true`` 的条目不入库

> ⚠️ **2026-09-20 重写**：原实现读的是 Nuxt 迁移前的
> ``frontend/web/src/router/routes.ts`` —— 该文件早已不存在，脚本一直以
> ``[ERROR] 未找到 ...`` 退出（过渡期只能靠 ``scripts/seed_batch*_menus.py`` 手工补行）。
> 现在改读 ``src/utils/menus.ts``，并顺带支持 ``hidden`` 与"与库内差异报告"。

用法::

    python -m scripts.seed_admin_menus                        # dry-run：解析结果 + 与库内差异
    python -m scripts.seed_admin_menus --apply                # 按 code upsert（幂等）
    python -m scripts.seed_admin_menus --apply --grant-system-roles
        # 额外把所有菜单授权给 is_system 角色

前置：先执行 ``alembic upgrade head``（admin_menus 表由 P3 迁移创建）。
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

#: 项目根由脚本自身位置推导，**不依赖当前工作目录**。
#: 早期实现写的是相对路径 ``Path("frontend/web/src/utils/menus.ts")``，在项目根之外的
#: 目录运行时会误报 ``[ERROR] 未找到 frontend/web/src/utils/menus.ts``（文件其实就在项目里）。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MENUS_TS = PROJECT_ROOT / "frontend" / "web" / "src" / "utils" / "menus.ts"

#: 取 `key: 'value'` / `key: 123` / `key: true`
_KV_RE = re.compile(r"(\w+)\s*:\s*(?:'([^']*)'|\"([^\"]*)\"|(true|false|-?\d+))")


def _kv(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, single, double, bare in _KV_RE.findall(text):
        result[key] = single or double or bare
    return result


def parse_menus_ts(text: str) -> list[dict]:
    """解析 ``ADMIN_MENUS`` 的对象字面量数组

    逐行扫描 + 层级栈，支持两种书写形态（本文件两种混用）：

    - **单行条目**：``{name: 'X', path: '...', title: '...', permission: '...'},``
    - **多行条目**：``{`` / 若干 ``key: value,`` / ``},``

    以及 ``children: [ ... ]`` 嵌套。产出顺序**父先于子**（后续按 code upsert 依赖这一点）。
    """
    entries: list[dict] = []
    parents: list[dict | None] = []  # 每一层的父条目
    pending: dict | None = None  # 正在累积的多行条目

    def _attach(entry: dict) -> None:
        # `name` → `code` 统一在这里做：多行父条目（走 children 分支压栈）也必须先转换，
        # 否则其子条目取 parent["code"] 会 KeyError
        if entry.get("name"):
            entry["code"] = entry.pop("name")
        parent = parents[-1] if parents else None
        entry["parent_code"] = parent["code"] if parent else None
        entries.append(entry)

    for raw in text.splitlines():
        line = raw.split("//")[0].strip()
        if not line or line.startswith("*") or line.startswith("/*"):
            continue

        if line.startswith("children:"):
            # 当前条目升级为父：先产出它，再压栈
            if pending is not None:
                pending["has_children"] = True
                _attach(pending)
                parents.append(pending)
                pending = None
            continue

        if line.startswith("]"):
            if parents:
                parents.pop()
            continue

        has_open = "{" in line
        has_close = "}" in line

        if has_open and has_close:
            data = _kv(line)
            if data.get("name"):
                _attach(data)
            continue

        if has_open:
            pending = _kv(line)
            continue

        if pending is not None:
            pending.update(_kv(line))
            if has_close:
                if pending.get("name"):
                    _attach(pending)
                pending = None
            continue

    return entries


def to_menu_rows(entries: list[dict]) -> list[dict]:
    """把解析结果转成 ``admin_menus`` 行（跳过 ``hidden``）"""
    rows: list[dict] = []
    for order, entry in enumerate(entries):
        if str(entry.get("hidden", "")).lower() == "true":
            continue
        code = entry.get("code")
        if not code:
            continue
        raw_sort = str(entry.get("order", ""))
        sort_order = int(raw_sort) if raw_sort.lstrip("-").isdigit() else order
        rows.append(
            {
                "code": code,
                "title": entry.get("title") or code,
                "parent_code": entry.get("parent_code"),
                "menu_type": 1 if entry.get("has_children") else 2,
                "permission_code": entry.get("permission") or None,
                "sort_order": sort_order,
                "is_active": True,
            }
        )
    return rows


def load_all_models() -> None:
    """显式加载全部 ORM 模型

    ``shared/models/__init__.py`` 采用懒加载（模块级 ``__getattr__``），只导入部分模型时，
    ``relationship`` 的字符串目标（如 ``'User'``）会解析失败并抛
    ``InvalidRequestError: ... failed to locate a name``。
    独立脚本必须先把全部模型注册进 registry（做法与 ``alembic_migrations/env.py`` 一致）。
    """
    import importlib

    from shared.models import _LAZY_IMPORTS

    for module in sorted(set(_LAZY_IMPORTS.values())):
        importlib.import_module(f"shared.models{module}")


async def apply_rows(rows: list[dict], *, grant_system_roles: bool) -> None:
    from sqlalchemy import select

    load_all_models()

    from shared.models.rbac.admin_menu import AdminMenu
    from shared.models.rbac.role import Role
    from shared.models.rbac.role_admin_menu import RoleAdminMenu
    from shared.models.rbac.user_role import UserRole
    from src.api.v3.modules.system.admin_menu.crud import admin_menu_crud
    from src.utils.database.unified_manager import db_manager

    async with db_manager.get_session() as db:
        existing_list, _total = await admin_menu_crud.list(db, page=1, page_size=0)
        by_code = {menu.code: menu for menu in existing_list}

        created = updated = 0
        for row in rows:
            parent = by_code.get(row["parent_code"]) if row["parent_code"] else None
            if row["parent_code"] and parent is None:
                print(f"  [WARN] {row['code']} 的父菜单 {row['parent_code']} 不存在，挂到根下")
            data = {
                "code": row["code"],
                "title": row["title"],
                "parent_id": parent.id if parent is not None else None,
                "menu_type": row["menu_type"],
                "permission_code": row["permission_code"],
                "sort_order": row["sort_order"],
                "is_active": True,
            }
            menu = by_code.get(row["code"])
            if menu is None:
                menu = await admin_menu_crud.create(db, data)
                by_code[row["code"]] = menu
                created += 1
            else:
                await admin_menu_crud.update(db, menu, data)
                updated += 1
        print(f"  admin_menus: 新建 {created} / 更新 {updated}")

        # 库里存在、但 menus.ts 已经没有的 code —— 只报告，**不删**（可能是插件页或过渡期手工行）
        stale = sorted(set(by_code) - {row["code"] for row in rows})
        if stale:
            print(f"  [提示] 库内还有 {len(stale)} 个菜单不在 menus.ts 中（未处理）：{stale}")

        if grant_system_roles:
            menu_ids = list((await db.execute(select(AdminMenu.id))).scalars().all())
            role_ids = (
                (await db.execute(select(Role.id).where(Role.is_system.is_(True)))).scalars().all()
            )
            if not role_ids:
                # 没有系统角色时，退化为"被任意用户持有的角色"
                role_ids = (
                    (
                        await db.execute(
                            select(UserRole.role_id)
                            .join(Role, Role.id == UserRole.role_id)
                            .where(Role.is_active.is_(True))
                        )
                    )
                    .scalars()
                    .all()
                )
            granted = 0
            for role_id in set(role_ids):
                current = set(
                    (
                        await db.execute(
                            select(RoleAdminMenu.admin_menu_id).where(
                                RoleAdminMenu.role_id == role_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                for menu_id in menu_ids:
                    if menu_id not in current:
                        db.add(RoleAdminMenu(role_id=role_id, admin_menu_id=menu_id))
                        granted += 1
            await db.commit()
            print(
                f"  角色授权: 新增 {granted} 条（角色 {len(set(role_ids))} 个 × 菜单 {len(menu_ids)} 个）"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="由前端 menus.ts 生成后台菜单种子")
    parser.add_argument("--apply", action="store_true", help="写库（默认仅 dry-run）")
    parser.add_argument("--grant-system-roles", action="store_true", help="额外把全部菜单授权给系统角色")
    args = parser.parse_args(argv)

    if not MENUS_TS.exists():
        print(f"[ERROR] 未找到 {MENUS_TS}", file=sys.stderr)
        return 1

    entries = parse_menus_ts(MENUS_TS.read_text(encoding="utf-8"))
    rows = to_menu_rows(entries)
    dirs = sum(1 for row in rows if row["menu_type"] == 1)
    print(f"解析 {MENUS_TS}: 条目 {len(entries)} 条 → 菜单 {len(rows)} 条（目录 {dirs} / 菜单 {len(rows) - dirs}）")
    for row in rows:
        parent = row["parent_code"] or "-"
        kind = {1: "目录", 2: "菜单", 3: "按钮"}.get(row["menu_type"], "?")
        print(
            f"  {row['code']:<20} {parent:<14} {kind}  sort={row['sort_order']:<3} "
            f"perm={row['permission_code'] or '-'}  {row['title']}"
        )

    if not args.apply:
        print("\n[dry-run] 未写库。确认无误后加 --apply")
        return 0

    asyncio.run(apply_rows(rows, grant_system_roles=args.grant_system_roles))
    print("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
