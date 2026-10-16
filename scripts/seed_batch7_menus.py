#!/usr/bin/env python3
"""T5-11 批次 7：admin_menus 补插 Commerce（目录）+ Payments / Revenue（子项）。

菜单 code 必须与前端 ``frontend/web/src/utils/menus.ts`` 的 ``name`` 一一对应
（``Commerce`` → ``/commerce``，``Payments`` → ``/commerce/payment``，
``Revenue`` → ``/commerce/revenue``）。

与前几批的差异：本批次有一个**新目录**（``Commerce``）作为父节点，所以脚本分两步 ——
先按 code upsert 目录，再用它的 id 建子项，**不硬编码任何菜单 id**。

用法::

    python -m scripts.seed_batch7_menus            # dry-run：只报告现状
    python -m scripts.seed_batch7_menus --apply    # 幂等写库（已存在的 code 跳过）
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
from datetime import datetime

from sqlalchemy import select

from shared.models import _LAZY_IMPORTS

for _m in sorted(set(_LAZY_IMPORTS.values())):
    importlib.import_module(f"shared.models{_m}")

from shared.models.rbac import AdminMenu  # noqa: E402
from src.utils.database.main import get_async_session_context  # noqa: E402

#: 新目录（commerce 域的总入口）
DIRECTORY: dict = {
    "code": "Commerce",
    "title": "Commerce",
    "permission_code": None,
    "sort_order": 9,
}

#: 目录下的子菜单
CHILDREN: list[dict] = [
    {
        "code": "Payments",
        "title": "Payments",
        "permission_code": "module_commerce:payment:view",
        "sort_order": 1,
    },
    {
        "code": "Revenue",
        "title": "Revenue Sharing",
        "permission_code": "module_commerce:revenue:view",
        "sort_order": 2,
    },
]


async def main(apply: bool) -> int:
    async with get_async_session_context() as db:
        # 1) 目录
        parent = (
            await db.execute(select(AdminMenu).where(AdminMenu.code == DIRECTORY["code"]))
        ).scalar_one_or_none()
        if parent is not None:
            print(f"  skip（已存在）: {DIRECTORY['code']} id={parent.id}")
        elif apply:
            now = datetime.now()
            parent = AdminMenu(
                code=DIRECTORY["code"],
                title=DIRECTORY["title"],
                parent_id=None,
                menu_type=1,
                permission_code=DIRECTORY["permission_code"],
                sort_order=DIRECTORY["sort_order"],
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(parent)
            await db.flush()
            print(f"  inserted 目录: {DIRECTORY['code']} id={parent.id}")
        else:
            print(f"  [dry-run] 待插入目录: {DIRECTORY['code']}")

        # 2) 子菜单（依赖目录 id，未写库时只能提示）
        for spec in CHILDREN:
            exists = (
                await db.execute(select(AdminMenu).where(AdminMenu.code == spec["code"]))
            ).scalar_one_or_none()
            if exists is not None:
                print(f"  skip（已存在）: {spec['code']} id={exists.id}")
                continue
            if not apply:
                print(f"  [dry-run] 待插入: {spec['code']} parent={DIRECTORY['code']}")
                continue
            now = datetime.now()
            db.add(
                AdminMenu(
                    code=spec["code"],
                    title=spec["title"],
                    parent_id=parent.id,
                    menu_type=2,
                    permission_code=spec["permission_code"],
                    sort_order=spec["sort_order"],
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            print(f"  inserted: {spec['code']} parent_id={parent.id}")

        if apply:
            await db.commit()
            print("[OK] 批次 7 菜单已写入（已存在的跳过）")
        else:
            print("[dry-run] 未写库。确认无误后加 --apply")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="补插 T5-11 批次 7 的后台菜单行")
    parser.add_argument("--apply", action="store_true", help="写库（默认仅 dry-run）")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.apply)))
