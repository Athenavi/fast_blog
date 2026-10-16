#!/usr/bin/env python3
"""T5-11 批次 6：admin_menus 补插 PageBuilder / Deployments / Enterprise 三行。

菜单 code 必须与前端 ``frontend/web/src/utils/menus.ts`` 的 ``name`` 一一对应
（``PageBuilder`` → ``/content/page-builder``，``Deployments`` → ``/ops/deployments``，
``Enterprise`` → ``/ops/enterprise``）。

父菜单按 **code** 查找（不硬编码 id，避免依赖具体库里的插入顺序）：
``Content``（内容管理）与 ``Ops``（运维）。找不到父菜单直接报错退出，
避免写出悬挂的 ``parent_id``。

用法::

    python -m scripts.seed_batch6_menus            # dry-run：只报告现状
    python -m scripts.seed_batch6_menus --apply    # 幂等写库（已存在的 code 跳过）

幂等：按 ``code`` 判断，已存在则跳过。
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import sys
from datetime import datetime

from sqlalchemy import select

from shared.models import _LAZY_IMPORTS

for _m in sorted(set(_LAZY_IMPORTS.values())):
    importlib.import_module(f"shared.models{_m}")

from shared.models.rbac import AdminMenu  # noqa: E402
from src.utils.database.main import get_async_session_context  # noqa: E402

#: 父菜单 code → 子菜单定义（顺序即 sort_order 依据）
NEW_MENUS: list[dict] = [
    {
        "code": "PageBuilder",
        "title": "Page Builder",
        "parent_code": "Content",
        "permission_code": "module_content:page_builder:view",
        "sort_order": 11,
    },
    {
        "code": "Deployments",
        "title": "Deploy Scripts",
        "parent_code": "Ops",
        "permission_code": "module_ops:deployment:view",
        "sort_order": 24,
    },
    {
        "code": "Enterprise",
        "title": "Enterprise License",
        "parent_code": "Ops",
        "permission_code": "module_ops:enterprise:view",
        "sort_order": 25,
    },
]


async def main(apply: bool) -> int:
    async with get_async_session_context() as db:
        # 父菜单 id 按 code 解析（Content / Ops 必须已存在）
        parent_ids: dict[str, int] = {}
        for code in {spec["parent_code"] for spec in NEW_MENUS}:
            parent = (
                await db.execute(select(AdminMenu).where(AdminMenu.code == code))
            ).scalar_one_or_none()
            if parent is None:
                print(f"[ERROR] 未找到父菜单 code={code}，请先跑 seed_admin_menus", file=sys.stderr)
                return 1
            parent_ids[code] = parent.id
            print(f"  父菜单 {code} → id={parent.id}")

        created = 0
        for spec in NEW_MENUS:
            exists = (
                await db.execute(select(AdminMenu).where(AdminMenu.code == spec["code"]))
            ).scalar_one_or_none()
            if exists:
                print(f"  skip（已存在）: {spec['code']} id={exists.id}")
                continue
            if not apply:
                print(f"  [dry-run] 待插入: {spec['code']} parent={spec['parent_code']}")
                continue
            db.add(
                AdminMenu(
                    code=spec["code"],
                    title=spec["title"],
                    parent_id=parent_ids[spec["parent_code"]],
                    menu_type=2,
                    permission_code=spec["permission_code"],
                    sort_order=spec["sort_order"],
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
            created += 1
            print(f"  inserted: {spec['code']}")

        if apply:
            await db.commit()
            print(f"[OK] 新增 {created} 行，其余跳过")
        else:
            print("[dry-run] 未写库。确认无误后加 --apply")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="补插 T5-11 批次 6 的后台菜单行")
    parser.add_argument("--apply", action="store_true", help="写库（默认仅 dry-run）")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.apply)))
