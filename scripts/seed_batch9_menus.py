#!/usr/bin/env python3
"""T5-11 批次 9：admin_menus 补插 Collaboration（协作管理）一行。

菜单 code 必须与前端 ``frontend/web/src/utils/menus.ts`` 的 ``name`` 一一对应
（``Collaboration`` → ``/content/collaboration``）。

父菜单按 **code** 查找（``Content``），不硬编码 id。

用法::

    python -m scripts.seed_batch9_menus            # dry-run：只报告现状
    python -m scripts.seed_batch9_menus --apply    # 幂等写库（已存在的 code 跳过）
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

NEW_MENUS: list[dict] = [
    {
        "code": "Collaboration",
        "title": "Collaboration",
        "parent_code": "Content",
        "permission_code": "module_content:collaboration:view",
        "sort_order": 12,
    },
]


async def main(apply: bool) -> int:
    async with get_async_session_context() as db:
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
            if exists is not None:
                print(f"  skip（已存在）: {spec['code']} id={exists.id}")
                continue
            if not apply:
                print(f"  [dry-run] 待插入: {spec['code']} parent={spec['parent_code']}")
                continue
            now = datetime.now()
            db.add(
                AdminMenu(
                    code=spec["code"],
                    title=spec["title"],
                    parent_id=parent_ids[spec["parent_code"]],
                    menu_type=2,
                    permission_code=spec["permission_code"],
                    sort_order=spec["sort_order"],
                    is_active=True,
                    created_at=now,
                    updated_at=now,
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
    parser = argparse.ArgumentParser(description="补插 T5-11 批次 9 的后台菜单行")
    parser.add_argument("--apply", action="store_true", help="写库（默认仅 dry-run）")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.apply)))
