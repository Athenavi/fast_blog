#!/usr/bin/env python3
"""T5-11 批次 4：admin_menus 补插多站点 / AI / 群聊 / CDN 菜单行。

幂等：按 code 判断已存在则跳过（含 AI 目录行）。
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

SYSTEM_PARENT_ID = 9  # 系统管理目录
OPS_PARENT_ID = 23  # 运维目录

# (code, title, parent_code_or_None, menu_type, permission_code, sort_order)
NEW_MENUS = [
    ("Sites", "Sites", "System", 2, "module_system:site:view", 23),
    ("AI", "AI", None, 1, None, 8),
    ("AIConfigs", "AI Configs", "AI", 2, "module_ai:config:view", 1),
    ("AIWorkflows", "AI Workflows", "AI", 2, "module_ai:workflow:view", 2),
    ("ChatGroups", "Chat Groups", None, 2, "module_chat:group:view", 7),
    ("CDN", "CDN", "Ops", 2, "module_ops:cdn:view", 22),
]


async def _parent_id(db, code: str | None) -> int | None:
    if code is None:
        return None
    row = (
        await db.execute(select(AdminMenu).where(AdminMenu.code == code))
    ).scalar_one_or_none()
    if row is None:
        raise SystemExit(f"父菜单不存在: {code}（应先插入目录行）")
    return row.id


async def main() -> None:
    async with get_async_session_context() as db:
        created = 0
        for code, title, parent_code, menu_type, perm, sort in NEW_MENUS:
            exists = (
                await db.execute(select(AdminMenu).where(AdminMenu.code == code))
            ).scalar_one_or_none()
            if exists:
                print(f"  skip（已存在）: {code} id={exists.id}")
                continue
            parent = await _parent_id(db, parent_code)
            db.add(
                AdminMenu(
                    code=code,
                    title=title,
                    parent_id=parent,
                    menu_type=menu_type,
                    permission_code=perm,
                    sort_order=sort,
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
            await db.commit()
            created += 1
            print(f"  inserted: {code} (parent={parent_code or 'root'})")
        print(f"[OK] 新增 {created} 行，其余跳过")


asyncio.run(main())
