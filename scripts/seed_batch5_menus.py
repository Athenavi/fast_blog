#!/usr/bin/env python3
"""T5-11 批次 5：admin_menus 补插 Upgrade（在线升级）与 ShortCodes（短代码）两行。

幂等：按 code 判断已存在则跳过。菜单 code 必须与前端 menus.ts 的 name 一致。
"""
import asyncio
import importlib
from datetime import datetime

from sqlalchemy import select

from shared.models import _LAZY_IMPORTS

for _m in sorted(set(_LAZY_IMPORTS.values())):
    importlib.import_module(f"shared.models{_m}")

from shared.models.rbac import AdminMenu
from src.utils.database.main import get_async_session_context

CONTENT_PARENT_ID = 2
OPS_PARENT_ID = 23

NEW_MENUS = [
    {"code": "ShortCodes", "title": "Shortcodes", "parent_id": CONTENT_PARENT_ID,
     "permission_code": "module_content:shortcode:view", "sort_order": 10},
    {"code": "Upgrade", "title": "Online Upgrade", "parent_id": OPS_PARENT_ID,
     "permission_code": "module_ops:upgrade:view", "sort_order": 23},
]


async def main() -> None:
    async with get_async_session_context() as db:
        created = 0
        for spec in NEW_MENUS:
            exists = (
                await db.execute(select(AdminMenu).where(AdminMenu.code == spec["code"]))
            ).scalar_one_or_none()
            if exists:
                print(f"  skip（已存在）: {spec['code']} id={exists.id}")
                continue
            db.add(
                AdminMenu(
                    code=spec["code"],
                    title=spec["title"],
                    parent_id=spec["parent_id"],
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
        await db.commit()
        print(f"[OK] 新增 {created} 行，其余跳过")


asyncio.run(main())
