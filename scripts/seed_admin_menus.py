"""后台菜单种子（源：``frontend/web/src/router/routes.ts``）

在"混合"决策下，**前端路由表是菜单结构的唯一真相**（后端只管"哪些菜单被授权"），
因此本脚本把路由表的 ``name`` / ``meta.title`` / ``meta.permission`` / 层级同步进
后端 ``admin_menus``：

  - ``code`` = 路由 ``name``（如 ``UserList``）
  - ``title`` = ``meta.title``
  - ``permission_code`` = ``meta.permission``
  - ``menu_type``：有子路由 → 1（目录），否则 2（菜单）
  - ``parent_id`` 由路由层级推导；``meta.hidden`` 的路由（登录/403/404）不入库

用法::

    python -m scripts.seed_admin_menus                        # dry-run：只打印解析结果
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

ROUTES_TS = Path("frontend/web/src/router/routes.ts")

#: 取 `key: 'value'` / `key: 123` / `key: true`
_KV_RE = re.compile(r"(\w+)\s*:\s*(?:'([^']*)'|\"([^\"]*)\"|(true|false|-?\d+))")


def _kv(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, single, double, bare in _KV_RE.findall(text):
        result[key] = single or double or bare
    return result


def parse_routes_ts(text: str) -> list[dict]:
    """从 routes.ts 提取菜单条目（保持父子顺序：父先于子）"""
    entries: list[dict] = []
    parents: dict[int, str] = {}
    depth = 0
    pending: dict | None = None
    meta_buffer: list[str] | None = None

    def flush() -> None:
        nonlocal pending
        if pending and pending.get("code"):
            entries.append(pending)
        pending = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("//", "/*", "*")):
            continue

        # 跨行 meta 的续行
        if meta_buffer is not None:
            meta_buffer.append(line)
            if "}" in line:
                pending.update(_kv(" ".join(meta_buffer)))  # type: ignore[union-attr]
                meta_buffer = None
            continue

        if line.startswith("children:"):
            if pending and pending.get("code"):
                parents[depth] = pending["code"]
                entries.append(pending)
                pending = None
            depth += 1
            continue

        if line.startswith("]"):
            flush()
            depth = max(depth - 1, 0)
            parents.pop(depth, None)
            continue

        if line.startswith("name:"):
            flush()
            pending = {"code": _kv(line).get("name")}
            # 当前路由的父：栈顶（depth-1 层）——depth=0 的顶级路由没有父
            pending["parent_code"] = parents.get(depth - 1)
            continue

        if line.startswith("meta:") and pending is not None:
            if "}" in line:
                pending.update(_kv(line))
            else:
                meta_buffer = [line]
            continue

    flush()
    return entries


def to_menu_rows(entries: list[dict]) -> list[dict]:
    """把解析结果转成 admin_menus 行（跳过 hidden 路由）"""
    # 先判断哪些 code 有子节点（用于 menu_type）
    has_children = {e["parent_code"] for e in entries if e.get("parent_code")}
    rows: list[dict] = []
    for order, entry in enumerate(entries):
        if entry.get("hidden") == "true":
            continue
        code = entry.get("code")
        if not code:
            continue
        rows.append(
            {
                "code": code,
                "title": entry.get("title") or code,
                "parent_code": entry.get("parent_code"),
                "menu_type": 1 if code in has_children else 2,
                "permission_code": entry.get("permission") or None,
                "sort_order": int(entry["order"]) if str(entry.get("order", "")).lstrip("-").isdigit() else order,
                "is_active": True,
            }
        )
    return rows


def load_all_models() -> None:
    """显式加载全部 ORM 模型

    ``shared/models/__init__.py`` 采用懒加载（模块级 ``__getattr__``），只导入部分模型时，
    ``relationship`` 的字符串目标（如 ``'User'``）会解析失败并抛
    ``InvalidRequestError: ... failed to locate a name ("name 'User' is not defined")``。
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

        if grant_system_roles:
            menu_ids = [
                menu.id for menu in (await db.execute(select(AdminMenu.id))).scalars().all()
            ]
            role_ids = (
                (await db.execute(select(Role.id).where(Role.is_system.is_(True)))).scalars().all()
            )
            if not role_ids:
                # 没有系统角色时，退化为"被超级管理员持有的角色"
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
            print(f"  角色授权: 新增 {granted} 条（角色 {len(set(role_ids))} 个 × 菜单 {len(menu_ids)} 个）")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="由前端路由表生成后台菜单种子")
    parser.add_argument("--apply", action="store_true", help="写库（默认仅 dry-run）")
    parser.add_argument("--grant-system-roles", action="store_true", help="额外把全部菜单授权给系统角色")
    args = parser.parse_args(argv)

    if not ROUTES_TS.exists():
        print(f"[ERROR] 未找到 {ROUTES_TS}", file=sys.stderr)
        return 1

    entries = parse_routes_ts(ROUTES_TS.read_text(encoding="utf-8"))
    rows = to_menu_rows(entries)
    print(f"解析 {ROUTES_TS}: 路由 {len(entries)} 条 → 菜单 {len(rows)} 条")
    for row in rows:
        parent = row["parent_code"] or "-"
        kind = {1: "目录", 2: "菜单", 3: "按钮"}.get(row["menu_type"], "?")
        print(
            f"  {row['code']:<20} {parent:<12} {kind}  sort={row['sort_order']:<3} "
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
