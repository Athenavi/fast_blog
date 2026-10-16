#!/usr/bin/env python3
"""T5-11 批次 3：admin_menus 补插 GDPR / Integrations / SocialAccounts / Security 四行。

幂等：按 code 判断已存在则跳过。
菜单 code 必须与前端 ``frontend/web/src/utils/menus.ts`` 的 name 一致。
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

SYSTEM_PARENT_ID = 9  # 系统管理目录（type=1, code=System）

NEW_MENUS = [
    {
        "code": "GDPR",
        "title": "GDPR",
        "permission_code": "module_system:gdpr:view",
        "sort_order": 19,
    },
    {
        "code": "Integrations",
        "title": "Integrations",
        "permission_code": "module_system:integration:view",
        "sort_order": 20,
    },
    {
        "code": "SocialAccounts",
        "title": "Social Accounts",
        "permission_code": "module_system:social:view",
        "sort_order": 21,
    },
    {
        "code": "Security",
        "title": "Security",
        "permission_code": "module_system:security:view",
        "sort_order": 22,
    },
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
                    parent_id=SYSTEM_PARENT_ID,
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
